import requests
import time
import pandas as pd
from datetime import datetime
import os
import sys

# Ensure src is in path if running from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.logger import setup_logger
from src.scraper import PlanszeoScraper
from src.bgg_api import BggApi
from src.notifier import EmailNotifier
from src.storage import load_json, save_json

logger = setup_logger()

def main():
    logger.info("🏆 Starting Planszeo Deals Scraper...")
    
    # Initialize components
    session = requests.Session()
    session.headers.update(Config.HEADERS)
    
    scraper = PlanszeoScraper(session)
    bgg_api = BggApi(session)
    notifier = EmailNotifier()
    
    # Load state
    last_checked_games = load_json(Config.LAST_CHECKED_FILE)
    last_checked_identifiers = set()
    for g in last_checked_games:
        if g.get('planszeo_url'): last_checked_identifiers.add(g['planszeo_url'])
        if g.get('nazwa'): last_checked_identifiers.add(g['nazwa'])

    logger.info(f"🔍 Last checked games: {[g.get('nazwa') for g in last_checked_games]}")
    
    all_games = []
    first_page_games = []
    found_last_checked = False
    max_pages = 10

    # Scrape loop
    for page in range(1, max_pages + 1):
        games_on_page = scraper.get_deals(page)
        if not games_on_page:
            break
        
        if page == 1:
            first_page_games = games_on_page

        # Check for duplicates/already seen
        if last_checked_identifiers:
            found_idx = -1
            for i, g in enumerate(games_on_page):
                if g['planszeo_url'] in last_checked_identifiers or g['nazwa'] in last_checked_identifiers:
                    found_idx = i
                    break
            
            if found_idx != -1:
                all_games.extend(games_on_page[:found_idx])
                logger.info(f"🎯 Found a previously checked game on page {page} at index {found_idx}. Stopping.")
                found_last_checked = True
                break 
        
        all_games.extend(games_on_page)
        time.sleep(1)

    if last_checked_identifiers and not found_last_checked:
        logger.warning(f"⚠️ None of the last checked games were found in the first {max_pages} pages. Scraping all games in these pages.")

    if not all_games:
        logger.info("No new games found.")
        if first_page_games:
            save_json(Config.LAST_CHECKED_FILE, [{'planszeo_url': g.get('planszeo_url'), 'nazwa': g.get('nazwa')} for g in first_page_games[:5]])
        return

    # Save new state
    if first_page_games:
        logger.info("💾 Updating last checked games with newest from page 1.")
        save_json(Config.LAST_CHECKED_FILE, [{'planszeo_url': g.get('planszeo_url'), 'nazwa': g.get('nazwa')} for g in first_page_games[:5]])
    
    logger.info(f"\n⭐ Scraping detailed information for {len(all_games)} new games...")
    
    # Process details
    for i, game in enumerate(all_games):
        logger.info(f"  ({i+1}/{len(all_games)}) Processing: {game['nazwa']}")

        details = scraper.get_details(game['planszeo_url'])
        game.update(details)

        bgg_stats = bgg_api.get_stats(game.get('bgg_url'))
        if bgg_stats:
            game.update(bgg_stats)
            
            # BGG Alert Logic
            if (bgg_stats.get('bgg_rank') and bgg_stats.get('bgg_rank') <= 200) or \
               (bgg_stats.get('bgg_rating') and bgg_stats.get('bgg_rating') > 8.0):
                subject = f"Planszeo Deal Alert: {game['nazwa']}"
                body = (
                    f"Game: {game['nazwa']}\n"
                    f"Price: {game['cena']:.2f} zł\n"
                    f"Discount: {game['obnizka']}\n"
                    f"Type: {game['typ']}\n"
                    f"BGG Rating: {bgg_stats.get('bgg_rating')}\n"
                    f"BGG Rank: {bgg_stats.get('bgg_rank')}\n"
                    f"Planszeo Link: {game.get('planszeo_url')}\n"
                    f"BGG Link: {game.get('bgg_url')}"
                )
                notifier.send(subject, body)

        elif ((game.get('planszeo_rating') and game.get('planszeo_rating') > 4.5 and game.get('planszeo_rating_count') and game.get('planszeo_rating_count') >= 50) or 
             (game.get('planszeo_rank') and game.get('planszeo_rank') <= 150)):
            subject = f"Planszeo Deal Alert: {game['nazwa']}"
            body = (
                f"Game: {game['nazwa']}\n"
                f"Price: {game['cena']:.2f} zł\n"
                f"Discount: {game['obnizka']}\n"
                f"Type: {game['typ']}\n"
                f"Planszeo Rating: {game.get('planszeo_rating')}\n"
                f"Planszeo Rating Count: {game.get('planszeo_rating_count')}\n"
                f"Planszeo Rank: {game.get('planszeo_rank')}\n"
                f"Planszeo Link: {game.get('planszeo_url')}\n"
            )
            notifier.send(subject, body)

        time.sleep(1.2)

    # Save CSV
    if all_games:
        df = pd.DataFrame(all_games)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = os.path.join(Config.DATA_DIR, f'planszeo_deals_{timestamp}.csv')
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')

        logger.info(f"\n✅ Scraping complete. Data saved to: {csv_file}")
        
        cols_to_show = ['nazwa', 'cena', 'obnizka', 'planszeo_rank', 'planszeo_rating', 'bgg_rank', 'bgg_rating']
        existing_cols = [c for c in cols_to_show if c in df.columns]
        logger.info("\n--- SCRAPED DATA ---\n" + df[existing_cols].to_string())

if __name__ == "__main__":
    main()
