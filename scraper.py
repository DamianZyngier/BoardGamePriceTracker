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

class PlanszeoScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.data_dir = 'data'
        os.makedirs(self.data_dir, exist_ok=True)
        self.history_file = os.path.join(self.data_dir, 'game_history.json')
        self.game_history = {}

    def scrape_ranking_page(self, page_num):
        """Scraps a single page of the Planszeo ranking."""
        url = f"https://planszeo.pl/top-listy/ranking?page={page_num}"
        print(f"📄 Scraping page {page_num}: {url}")

        try:
            resp = self.session.get(url)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"  Error fetching page {page_num}: {e}")
            return []

        soup = BeautifulSoup(resp.text, 'lxml')
        games = []
        
        game_items = soup.find_all('div', class_='flex relative flex-col gap-3 py-3 mx-auto mb-3 bg-white rounded-xl border shadow-sm transition-shadow border-bronze-200 hover:shadow-md lg:my-1')
        print(f"  📊 Found {len(game_items)} potential game items.")

        for item in game_items:
            try:
                # Extract Rank
                rank_tag = item.find('div', class_='text-base font-bold text-gray-700 lg:text-sm')
                rank = int(rank_tag.get_text(strip=True).split('.')[0]) if rank_tag else 0

                # Extract Game Name and URL
                name_div = item.find('div', class_='text-lg font-bold text-center text-gray-800 transition-colors group-hover:text-purple-600 lg:text-left')
                name = "N/A"
                game_url = None
                if name_div:
                    name = name_div.get_text(strip=True)
                    name_link_tag = name_div.find_parent('a')
                    if name_link_tag and 'href' in name_link_tag.attrs:
                        game_url = "https://planszeo.pl" + name_link_tag['href']

                games.append({
                    'miejsce': rank,
                    'nazwa': name,
                    'planszeo_url': game_url,
                })
            except Exception as e:
                print(f"  Error parsing an item: {e}")
                continue
        
        return games

    def get_planszeo_game_details(self, planszeo_url):
        """Extracts price, status, and Planszeo rating from an individual Planszeo game page."""
        if not planszeo_url:
            return {'cena': 0.0, 'status': 'N/A', 'planszeo_rating': None, 'bgg_url': None} # Added bgg_url to return

        print(f"    🛒 Visiting {planszeo_url} for price, status and Planszeo rating...")
        try:
            resp = self.session.get(planszeo_url, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'lxml')

            # Extract Price
            price = 0.0
            price_div = soup.find('div', class_='text-purple-500 font-extrabold text-lg lg:text-2xl mt-4')
            if price_div:
                price_str = price_div.get_text(strip=True).replace('zł', '').replace(',', '.').strip()
                price = float(price_str) if price_str and price_str != '-' else 0.0

            # Extract Planszeo Rating
            planszeo_rating = None
            rating_span = soup.find('span', class_='inline-flex items-center rounded-md bg-green-600/20 px-2 py-1 text-lg lg:text-xl font-bold text-green-600 ring-1 ring-inset ring-green-600/50')
            if rating_span:
                planszeo_rating = float(rating_span.get_text(strip=True))

            # Extract Status
            status = "N/A"
            # Using the new selector provided by the user
            status_div = soup.find('div', class_='text-green-600 text-xs flex flex-row px-0.5 items-center')
            if status_div:
                status_span = status_div.find('span', class_='ml-0.5 font-bold')
                if status_span:
                    status = status_span.get_text(strip=True)
            
            # Extract BGG Link from Planszeo game page
            bgg_link = None
            bgg_a = soup.find('a', href=re.compile(r'boardgamegeek.com/boardgame/'))
            if bgg_a and 'href' in bgg_a.attrs:
                bgg_link = bgg_a['href']
            
            return {'cena': price, 'status': status, 'planszeo_rating': planszeo_rating, 'bgg_url': bgg_link}

        except requests.exceptions.RequestException as e:
            print(f"      Could not fetch Planszeo game details: {e}")
        except Exception as e:
            print(f"      An error occurred while getting Planszeo game details: {e}")
        return {'cena': 0.0, 'status': 'N/A', 'planszeo_rating': None, 'bgg_url': None}

    def get_bgg_stats(self, bgg_url):
        """Gets rating and rank from a BGG page by scraping the embedded JSON data."""
        if not bgg_url:
            return {'bgg_rating': None, 'bgg_rank': None}

        print(f"    🎲 Visiting {bgg_url} for stats...")
        try:
            resp = self.session.get(bgg_url, timeout=15)
            resp.raise_for_status()

            # Find the JSON data embedded in the script tag
            match = re.search(r'GEEK\.geekitemPreload = (\{.*?\});', resp.text, re.DOTALL)
            if not match:
                print("      Could not find GEEK.geekitemPreload in the page.")
                return {'bgg_rating': None, 'bgg_rank': None}

            data = json.loads(match.group(1))
            item_data = data.get('item', {})

            # Extract rating
            rating = item_data.get('stats', {}).get('average')

            # Extract rank
            rank = None
            rank_info = item_data.get('rankinfo', [])
            for r in rank_info:
                if r.get('prettyname') == 'Board Game Rank':
                    rank_value = r.get('rank')
                    if rank_value and rank_value.isdigit():
                        rank = int(rank_value)
                    break
            
            return {'bgg_rating': rating, 'bgg_rank': rank}
        except requests.exceptions.RequestException as e:
            print(f"      Could not fetch BGG page: {e}")
        except json.JSONDecodeError as e:
            print(f"      Could not decode JSON from BGG page: {e}")
        except Exception as e:
            print(f"      An error occurred while getting BGG stats: {e}")
        return {'bgg_rating': None, 'bgg_rank': None}

    def send_email(self, subject, body):
        """Sends email notifications using environment variables for credentials."""
        sender_email = os.environ.get('EMAIL_SENDER')
        app_password = os.environ.get('EMAIL_APP_PASSWORD')
        receiver_email = 'zyngi23@gmail.com' # Fixed recipient email

        if not sender_email or not app_password:
            print("Email sending skipped: EMAIL_SENDER or EMAIL_APP_PASSWORD not set in environment variables.")
            print(f"\n--- EMAIL ALERT (skipped) ---")
            print(f"Subject: {subject}")
            print(f"Body:\n{body}")
            print(f"---------------------------\n")
            return

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = receiver_email

        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp: # Use SMTP_SSL for port 465
                smtp.login(sender_email, app_password)
                smtp.send_message(msg)
            print(f"Email sent successfully to {receiver_email}!")
        except Exception as e:
            print(f"Error sending email: {e}")

    def load_history(self):
        """Loads game history from a JSON file."""
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_history(self, history_data):
        """Saves game history to a JSON file."""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=4, ensure_ascii=False)

    def run_scraper(self, max_pages=20):
        """Main method to orchestrate the scraping process."""
        print("🏆 Starting Planszeo Scraper...")
        all_games = []
        for page in range(1, max_pages + 1):
            games_on_page = self.scrape_ranking_page(page)
            all_games.extend(games_on_page)
            if page < max_pages:
                time.sleep(1) # Be respectful to the server

        self.game_history = self.load_history()
        price_drop_alerts = []
        availability_alerts = []

        print("\n⭐ Scraping detailed information for each game and checking for price/availability changes...")
        for i, game in enumerate(all_games):
            print(f"  ({i+1}/{len(all_games)}) Processing: {game['nazwa']}")

            # Get Planszeo game details (price, status, planszeo_rating, bgg_url)
            planszeo_details = self.get_planszeo_game_details(game['planszeo_url'])
            
            # Get historical data for this game
            historical_data = self.game_history.get(game['planszeo_url'], {})
            
            old_price = historical_data.get('cena')
            old_status = historical_data.get('status')
            
            current_price = planszeo_details.get('cena')
            current_status = planszeo_details.get('status')
            game_name = game['nazwa']

            # Check for price drop
            if old_price is not None and current_price is not None and old_price > 0:
                price_change = (old_price - current_price) / old_price
                if price_change >= 0.20: # 20% price drop
                    alert_message = (
                        f"📈 Price Drop Alert for {game_name}!\n"
                        f"Previous Price: {old_price:.2f} zł\n"
                        f"Current Price: {current_price:.2f} zł\n"
                        f"Drop: {price_change:.2%}\n"
                        f"Link: {game['planszeo_url']}"
                    )
                    price_drop_alerts.append(alert_message)
            
            # Check for availability change (was unavailable, now available)
            unavailability_keywords = ["n/a", "niedostępna", "brak w magazynie"] # Customize as needed
            availability_keywords = ["dostępna", "w magazynie"] # Customize as needed

            if old_status and current_status and \
               any(keyword in old_status.lower() for keyword in unavailability_keywords) and \
               any(keyword in current_status.lower() for keyword in availability_keywords):
                alert_message = (
                    f"✅ Availability Alert for {game_name}!\n"
                    f"Game was '{old_status}', now '{current_status}'.\n"
                    f"Link: {game['planszeo_url']}"
                )
                availability_alerts.append(alert_message)


            game.update(planszeo_details) # This will also add 'bgg_url' now

            # Get BGG details (using bgg_url from planszeo_details)
            bgg_stats = self.get_bgg_stats(game['bgg_url'])
            game.update(bgg_stats)
            
            # Update history for this game
            self.game_history[game['planszeo_url']] = {
                'nazwa': game_name,
                'cena': current_price,
                'status': current_status,
                'planszeo_rating': planszeo_details.get('planszeo_rating'),
                'timestamp': datetime.now().isoformat()
            }
            
            time.sleep(1.2) # Be extra respectful to BGG API

        # Send email alerts if any changes were detected
        all_alerts = price_drop_alerts + availability_alerts
        if all_alerts:
            subject = "Planszeo.pl - Board Game Alerts!"
            body = "\n\n".join(all_alerts)
            self.send_email(subject, body)
        else:
            print("\n🔔 No significant changes detected today.")

        # Save updated history
        self.save_history(self.game_history)

        df = pd.DataFrame(all_games)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = os.path.join(self.data_dir, f'planszeo_ranking_{timestamp}.csv')
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')

        print(f"\n✅ Scraping complete. Data saved to: {csv_file}")
        print("\n📊 First 10 results:")
        print(df.head(10).to_string())

if __name__ == "__main__":
    scraper = PlanszeoScraper()
    # For testing, we scrape only 1 page as requested.
    # To scrape all 20 pages, change max_pages to 20.
    scraper.run_scraper(max_pages=1)

