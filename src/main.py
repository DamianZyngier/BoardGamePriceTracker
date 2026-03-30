import os
import requests
import time
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Set, Tuple

from src.config import settings
from src.logger import setup_logger
from src.scraper import PlanszeoScraper
from src.bgg_api import BggApi
from src.notifier import EmailNotifier
from src.storage import load_json, save_json
from src.models import PlanszeoDeal, GameDetails
from src.page_generator import generate_html, save_page

logger = setup_logger()

NOTIFICATION_THRESHOLDS = (
    "- BGG Rank <= 200\n"
    "- BGG Rating > 8.0\n"
    "- Planszeo Rank <= 150\n"
    "- Planszeo Rating > 4.5 AND Rating Count >= 50"
)

class BoardGameTracker:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(settings.headers)
        
        self.scraper = PlanszeoScraper(self.session)
        self.bgg_api = BggApi(self.session)
        self.notifier = EmailNotifier()
        
        self.last_checked_identifiers: Set[str] = self._load_last_checked()
        self.stats_file = os.path.join(settings.DATA_DIR, 'stats.json')

    def _load_last_checked(self) -> Set[str]:
        last_checked_games = load_json(settings.last_checked_file)
        identifiers = set()
        for g in last_checked_games:
            if isinstance(g, dict):
                if g.get('planszeo_url'): identifiers.add(str(g['planszeo_url']))
                if g.get('nazwa'): identifiers.add(g['nazwa'])
        logger.info(f"🔍 Loaded {len(identifiers)} last checked identifiers.")
        return identifiers

    def _save_last_checked(self, deals: List[PlanszeoDeal]):
        if not deals: return
        data = [{'planszeo_url': str(g.planszeo_url), 'nazwa': g.nazwa} for g in deals[:5]]
        save_json(settings.last_checked_file, data)
        logger.info("💾 Updated last checked games.")

    def run(self, max_pages: int = 10):
        logger.info("🏆 Starting BoardGamePriceTracker...")
        
        now = datetime.now(ZoneInfo("Europe/Warsaw"))
        stats = load_json(self.stats_file)
        if not isinstance(stats, dict):
            stats = {
                "last_run": "Never",
                "last_new_deals_date": "Never",
                "last_notification_date": "Never",
                "last_notification_game": "N/A",
                "last_notification_url": "#",
                "last_deals": []
            }

        stats["last_run"] = now.strftime('%Y-%m-%d %H:%M:%S')
        
        new_deals, first_page_deals = self._scrape_new_deals(max_pages)
        
        processed_games = []
        if new_deals:
            processed_games = self._process_deals(new_deals)
            self._export_results(processed_games)
            
            stats["last_new_deals_date"] = stats["last_run"]
            stats["last_deals"] = [g.model_dump(mode='json') for g in processed_games]
            
            # Check for alerts and update last_notification stats
            for game in processed_games:
                if game.passed_threshold:
                    stats["last_notification_date"] = stats["last_run"]
                    stats["last_notification_game"] = game.nazwa
                    stats["last_notification_url"] = str(game.planszeo_url)
                    # We only store the latest notification info for the page
            
            # Save the very first deals found on page 1 as the new "last checked" state
            if first_page_deals:
                self._save_last_checked(first_page_deals)
        else:
            logger.info("No new deals found.")
            # Still update last checked if we found something on page 1
            if first_page_deals:
                self._save_last_checked(first_page_deals)

        # Update stats file
        save_json(self.stats_file, stats)
        
        # Generate GitHub Pages
        html = generate_html(
            last_run=stats["last_run"],
            last_new_deals_date=stats["last_new_deals_date"],
            last_notification_date=stats.get("last_notification_date", "Never"),
            last_notification_game=stats.get("last_notification_game", "N/A"),
            last_notification_url=stats.get("last_notification_url", "#"),
            thresholds=NOTIFICATION_THRESHOLDS,
            deals=stats["last_deals"]
        )
        save_page(html)
        logger.info("🌐 GitHub Pages site generated in docs/index.html")

    def _scrape_new_deals(self, max_pages: int) -> Tuple[List[PlanszeoDeal], List[PlanszeoDeal]]:
        all_new_deals = []
        first_page_deals = []

        for page in range(1, max_pages + 1):
            deals_on_page = self.scraper.get_deals(page)
            if not deals_on_page:
                break
            
            if page == 1:
                first_page_deals = deals_on_page

            found_idx = -1
            for i, deal in enumerate(deals_on_page):
                if str(deal.planszeo_url) in self.last_checked_identifiers or deal.nazwa in self.last_checked_identifiers:
                    found_idx = i
                    break
            
            if found_idx != -1:
                all_new_deals.extend(deals_on_page[:found_idx])
                logger.info(f"🎯 Found a previously checked game on page {page}. Stopping.")
                break 
            
            all_new_deals.extend(deals_on_page)
            time.sleep(1)

        return all_new_deals, first_page_deals

    def _process_deals(self, deals: List[PlanszeoDeal]) -> List[GameDetails]:
        logger.info(f"\n⭐ Processing {len(deals)} new deals...")
        processed_games = []

        for i, deal in enumerate(deals):
            logger.info(f"  ({i+1}/{len(deals)}) Processing: {deal.nazwa}")
            
            # 1. Get Planszeo Details (Rank, Rating, BGG Link)
            enriched_deal = self.scraper.get_details(deal)
            
            # 2. Get BGG Stats
            bgg_stats = self.bgg_api.get_stats(str(enriched_deal.bgg_url)) if enriched_deal.bgg_url else None
            
            # 3. Combine into GameDetails
            game = GameDetails(
                **enriched_deal.model_dump(),
                bgg_rating=bgg_stats.bgg_rating if bgg_stats else None,
                bgg_rank=bgg_stats.bgg_rank if bgg_stats else None
            )
            
            # 4. Check for Alerts
            self._check_alerts(game)
            
            processed_games.append(game)
            time.sleep(1.2)
            
        return processed_games

    def _check_alerts(self, game: GameDetails):
        subject = f"Planszeo Deal Alert: {game.nazwa}"
        should_notify = False
        criteria = ""

        # BGG Logic
        if game.bgg_rank and game.bgg_rank <= 200:
            should_notify = True
            criteria += f"- BGG Top 200 Rank: {game.bgg_rank}\n"
        if game.bgg_rating and game.bgg_rating > 8.0:
            should_notify = True
            criteria += f"- BGG High Rating: {game.bgg_rating}\n"
            
        # Planszeo Logic (fallback if BGG missing or as extra criteria)
        if not should_notify:
            if game.planszeo_rank and game.planszeo_rank <= 150:
                should_notify = True
                criteria += f"- Planszeo Top 150 Rank: {game.planszeo_rank}\n"
            elif game.planszeo_rating and game.planszeo_rating > 4.5 and game.planszeo_rating_count and game.planszeo_rating_count >= 50:
                should_notify = True
                criteria += f"- Planszeo High Rating: {game.planszeo_rating} ({game.planszeo_rating_count} votes)\n"

        game.passed_threshold = should_notify
        if should_notify:
            body = (
                f"Game: {game.nazwa}\n"
                f"Price: {game.cena:.2f} zł\n"
                f"Discount: {game.obnizka}\n"
                f"Type: {game.typ}\n\n"
                f"Alert Criteria:\n{criteria}\n"
                f"Links:\n"
                f"- Planszeo: {game.planszeo_url}\n"
                f"- BGG: {game.bgg_url or 'N/A'}"
            )
            self.notifier.send(subject, body)

    def _export_results(self, games: List[GameDetails]):
        if not games: return
        
        df = pd.DataFrame([g.model_dump() for g in games])
        timestamp = datetime.now(ZoneInfo("Europe/Warsaw")).strftime('%Y%m%d_%H%M%S')
        csv_file = os.path.join(settings.DATA_DIR, f'planszeo_deals_{timestamp}.csv')
        os.makedirs(settings.DATA_DIR, exist_ok=True)
        
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        logger.info(f"\n✅ Scraping complete. Data saved to: {csv_file}")
        
        cols = ['nazwa', 'cena', 'obnizka', 'planszeo_rank', 'bgg_rank', 'bgg_rating']
        existing_cols = [c for c in cols if c in df.columns]
        logger.info("\n--- NEW DEALS ---\n" + df[existing_cols].to_string())

if __name__ == "__main__":
    tracker = BoardGameTracker()
    tracker.run()
