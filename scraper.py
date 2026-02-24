import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import os
import json
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PlanszeoScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.data_dir = 'data'
        os.makedirs(self.data_dir, exist_ok=True)
        self.history_file = os.path.join(self.data_dir, 'game_history.json')
        self.last_checked_games_file = os.path.join(self.data_dir, 'last_checked_games.json')
        self.game_history = {}

    def scrape_deals_page(self, page_num):
        """Scraps a single page of the Planszeo deals."""
        url = f"https://planszeo.pl/okazje?page={page_num}"
        logging.info(f"📄 Scraping page {page_num}: {url}")

        try:
            resp = self.session.get(url)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"  Error fetching page {page_num}: {e}")
            return []

        soup = BeautifulSoup(resp.text, 'html.parser') # Use html.parser instead of lxml
        games = []
        
        game_items = soup.find_all('div', class_='flex relative flex-col gap-3 py-3 mx-auto mb-3 bg-white rounded-xl border shadow-sm transition-shadow border-bronze-200 hover:shadow-md lg:my-1')
        logging.info(f"  📊 Found {len(game_items)} potential game items.")

        for item in game_items:
            try:
                name_div = item.find('div', class_='text-lg font-bold text-center text-gray-800 transition-colors group-hover:text-purple-600 lg:text-left')
                name = "N/A"
                game_url = None
                if name_div:
                    name = name_div.get_text(strip=True)
                    name_link_tag = name_div.find_parent('a')
                    if name_link_tag and 'href' in name_link_tag.attrs:
                        game_url = "https://planszeo.pl" + name_link_tag['href']

                price_span = item.find('span', class_='text-lg font-extrabold text-purple-500 whitespace-nowrap')
                price_str = price_span.get_text(strip=True).replace('zł', '').replace(',', '.').strip() if price_span else '0'
                price = float(price_str) if price_str else 0.0

                discount_div = item.find('div', class_='inline-flex gap-1 items-center px-2.5 py-1 mt-1 text-sm font-bold rounded-lg ring-1 ring-inset text-gray-purple-800 bg-gray-purple-800/20 ring-gray-purple-800/50')
                discount = discount_div.get_text(strip=True) if discount_div else '0%'

                game_type_div = item.find('div', class_=re.compile(r'bg-yellow-50|bg-green-50'))
                game_type = 'Dodatek' if game_type_div and 'bg-yellow-50' in game_type_div['class'] else 'Gra podstawowa'

                games.append({
                    'nazwa': name,
                    'cena': price,
                    'obnizka': discount,
                    'typ': game_type,
                    'planszeo_url': game_url,
                })
            except Exception as e:
                logging.error(f"  Error parsing an item: {e}")
                continue
        
        return games

    def get_planszeo_game_details(self, planszeo_url):
        """Extracts BGG link, Planszeo rank, rating, and rating count from an individual Planszeo game page."""
        if not planszeo_url:
            return {'bgg_url': None, 'planszeo_rank': None, 'planszeo_rating': None, 'planszeo_rating_count': None}

        logging.info(f"    🛒 Visiting {planszeo_url} for Planszeo details and BGG link...")
        try:
            resp = self.session.get(planszeo_url, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            bgg_link = None
            bgg_a = soup.find('a', href=re.compile(r'boardgamegeek.com/boardgame/'))
            if bgg_a and 'href' in bgg_a.attrs:
                bgg_link = bgg_a['href']
            
            planszeo_rank = None
            rank_div = soup.find('div', class_='inline-flex items-center rounded-md bg-gray-purple-800/20 px-2 py-1 text-lg font-bold text-gray-purple-800 ring-1 ring-inset ring-gray-purple-800/50')
            if rank_div:
                rank_text = rank_div.find('div').get_text(strip=True)
                if rank_text:
                    planszeo_rank = int(rank_text.split('.')[0])

            planszeo_rating = None
            rating_span = soup.find('span', class_='inline-flex items-center rounded-md bg-green-600/20 px-2 py-1 text-lg lg:text-xl font-bold text-green-600 ring-1 ring-inset ring-green-600/50')
            if rating_span:
                planszeo_rating = float(rating_span.get_text(strip=True))

            planszeo_rating_count = None
            if rating_span:
                rating_count_div = rating_span.find_parent('div').find_next_sibling('div', class_='text-xs')
                if rating_count_div:
                    rating_count_text = rating_count_div.get_text(strip=True).split(' ')[0]
                    if rating_count_text.isdigit():
                        planszeo_rating_count = int(rating_count_text)

            return {'bgg_url': bgg_link, 'planszeo_rank': planszeo_rank, 'planszeo_rating': planszeo_rating, 'planszeo_rating_count': planszeo_rating_count}

        except requests.exceptions.RequestException as e:
            logging.error(f"      Could not fetch Planszeo game details: {e}")
        except Exception as e:
            logging.error(f"      An error occurred while getting Planszeo game details: {e}")
        return {'bgg_url': None, 'planszeo_rank': None, 'planszeo_rating': None, 'planszeo_rating_count': None}

    def get_bgg_stats(self, bgg_url):
        """Gets rating and rank from a BGG page by scraping the embedded JSON data."""
        # This function is commented out as direct scraping of BGG is blocked by Cloudflare
        # and API key was not provided.
        return None

    def send_email(self, subject, body):
        """Sends email notifications using environment variables for credentials."""
        sender_email = os.environ.get('EMAIL_SENDER')
        app_password = os.environ.get('EMAIL_APP_PASSWORD')
        receiver_email = 'zyngi23@gmail.com'

        if not sender_email or not app_password:
            logging.warning("Email sending skipped: EMAIL_SENDER or EMAIL_APP_PASSWORD not set in environment variables.")
            logging.info(f"\n--- EMAIL ALERT (skipped) ---\nSubject: {subject}\nBody:\n{body}\n---------------------------\n")
            return

        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(sender_email, app_password)
                smtp.send_message(msg)
            logging.info(f"Email sent successfully to {receiver_email}!")
        except Exception as e:
            logging.error(f"Error sending email: {e}")

    def get_last_checked_games(self):
        if os.path.exists(self.last_checked_games_file):
            try:
                with open(self.last_checked_games_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error reading last checked games: {e}")
        return []

    def save_last_checked_games(self, games_list):
        # Save up to 5 newest games (URLs or names)
        to_save = []
        for g in games_list[:5]:
            to_save.append({
                'planszeo_url': g.get('planszeo_url'),
                'nazwa': g.get('nazwa')
            })
        
        with open(self.last_checked_games_file, 'w', encoding='utf-8') as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)
    
    def run_scraper(self, max_pages=10):
        logging.info("🏆 Starting Planszeo Deals Scraper...")
        all_games = []
        last_checked_games = self.get_last_checked_games()
        last_checked_identifiers = set()
        for g in last_checked_games:
            if g.get('planszeo_url'): last_checked_identifiers.add(g['planszeo_url'])
            if g.get('nazwa'): last_checked_identifiers.add(g['nazwa'])

        logging.info(f"🔍 Last checked games: {[g.get('nazwa') for g in last_checked_games]}")
        
        found_last_checked = False
        first_page_games = []

        for page in range(1, max_pages + 1):
            games_on_page = self.scrape_deals_page(page)
            if not games_on_page:
                break
            
            if page == 1:
                first_page_games = games_on_page

            if last_checked_identifiers:
                found_idx = -1
                for i, g in enumerate(games_on_page):
                    if g['planszeo_url'] in last_checked_identifiers or g['nazwa'] in last_checked_identifiers:
                        found_idx = i
                        break
                
                if found_idx != -1:
                    all_games.extend(games_on_page[:found_idx])
                    logging.info(f"🎯 Found a previously checked game on page {page} at index {found_idx}. Stopping.")
                    found_last_checked = True
                    break 
            
            all_games.extend(games_on_page)
            time.sleep(1)

        if last_checked_identifiers and not found_last_checked:
            logging.warning(f"⚠️ None of the last checked games were found in the first {max_pages} pages. Scraping all games in these pages.")

        if not all_games:
            logging.info("No new games found.")
            # Still update last checked games from page 1 to keep them fresh
            if first_page_games:
                self.save_last_checked_games(first_page_games)
            return

        # Save the newest games from this run
        # We take them from first_page_games to ensure we have the absolute newest
        if first_page_games:
            logging.info(f"💾 Updating last checked games with newest from page 1.")
            self.save_last_checked_games(first_page_games)
        
        logging.info(f"\n⭐ Scraping detailed information for {len(all_games)} new games...")
        for i, game in enumerate(all_games):
            logging.info(f"  ({i+1}/{len(all_games)}) Processing: {game['nazwa']}")

            planszeo_details = self.get_planszeo_game_details(game['planszeo_url'])
            game.update(planszeo_details)

            # bgg_stats = self.get_bgg_stats(game.get('bgg_url'))
            # if bgg_stats:
            #     game.update(bgg_stats)
            #
            #     if (bgg_stats.get('bgg_rank') and bgg_stats.get('bgg_rank') >= 300) or \
            #        (bgg_stats.get('bgg_rating') and bgg_stats.get('bgg_rating') > 7.5):
            #         subject = f"Planszeo Deal Alert: {game['nazwa']}"
            #         body = (
            #             f"Game: {game['nazwa']}\n"
            #             f"Price: {game['cena']:.2f} zł\n"
            #             f"Discount: {game['obnizka']}\n"
            #             f"Type: {game['typ']}\n"
            #             f"BGG Rating: {bgg_stats.get('bgg_rating')}\n"
            #             f"BGG Rank: {bgg_stats.get('bgg_rank')}\n"
            #             f"Planszeo Link: {game.get('planszeo_url')}\n"
            #             f"BGG Link: {game.get('bgg_url')}"
            #         )
            #         self.send_email(subject, body)

            if (game.get('planszeo_rating') and game.get('planszeo_rating') > 4.0 and game.get('planszeo_rating_count') and game.get('planszeo_rating_count') >= 10) or \
               (game.get('planszeo_rank') and game.get('planszeo_rank') <= 200):
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
                self.send_email(subject, body)

            time.sleep(1.2)

        df = pd.DataFrame(all_games)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = os.path.join(self.data_dir, f'planszeo_deals_{timestamp}.csv')
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')

        logging.info(f"\n✅ Scraping complete. Data saved to: {csv_file}")
        
        if not df.empty:
            logging.info("\n--- SCRAPED DATA ---\n" + df[['nazwa', 'cena', 'obnizka', 'typ', 'planszeo_url', 'planszeo_rank', 'planszeo_rating', 'planszeo_rating_count']].to_string())

if __name__ == "__main__":
    scraper = PlanszeoScraper()
    scraper.run_scraper()
