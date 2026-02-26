import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any, Optional

from src.config import settings
from src.logger import setup_logger
from src.models import PlanszeoDeal

logger = setup_logger(__name__)

class PlanszeoScraper:
    def __init__(self, session: requests.Session):
        self.session = session
        self.base_url = settings.PLANSZEO_BASE_URL
        self.deals_url = settings.PLANSZEO_DEALS_URL

    def get_deals(self, page_num: int) -> List[PlanszeoDeal]:
        """Scraps a single page of the Planszeo deals."""
        url = f"{self.deals_url}?page={page_num}"
        logger.info(f"📄 Scraping page {page_num}: {url}")

        try:
            resp = self.session.get(url)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"  Error fetching page {page_num}: {e}")
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')
        deals = []
        
        game_items = soup.find_all('div', class_='flex relative flex-col gap-3 py-3 mx-auto mb-3 bg-white rounded-xl border shadow-sm transition-shadow border-bronze-200 hover:shadow-md lg:my-1')
        logger.info(f"  📊 Found {len(game_items)} potential game items.")

        for item in game_items:
            try:
                name_div = item.find('div', class_='text-lg font-bold text-center text-gray-800 transition-colors group-hover:text-purple-600 lg:text-left')
                name = "N/A"
                game_url = None
                if name_div:
                    name = name_div.get_text(strip=True)
                    name_link_tag = name_div.find_parent('a')
                    if name_link_tag and 'href' in name_link_tag.attrs:
                        game_url = self.base_url + name_link_tag['href']

                price_span = item.find('span', class_='text-lg font-extrabold text-purple-500 whitespace-nowrap')
                price_str = price_span.get_text(strip=True).replace('zł', '').replace(',', '.').strip() if price_span else '0'
                price = float(price_str) if price_str else 0.0

                discount_div = item.find('div', class_='inline-flex gap-1 items-center px-2.5 py-1 mt-1 text-sm font-bold rounded-lg ring-1 ring-inset text-gray-purple-800 bg-gray-purple-800/20 ring-gray-purple-800/50')
                discount = discount_div.get_text(strip=True) if discount_div else '0%'

                game_type_div = item.find('div', class_=re.compile(r'bg-yellow-50|bg-green-50'))
                game_type = 'Dodatek' if game_type_div and 'bg-yellow-50' in game_type_div['class'] else 'Gra podstawowa'

                if game_url:
                    deals.append(PlanszeoDeal(
                        nazwa=name,
                        cena=price,
                        obnizka=discount,
                        typ=game_type,
                        planszeo_url=game_url,
                    ))
            except Exception as e:
                logger.error(f"  Error parsing an item: {e}")
                continue
        
        return deals

    def get_details(self, deal: PlanszeoDeal) -> PlanszeoDeal:
        """Enriches the deal with BGG link, Planszeo rank, rating, and rating count."""
        logger.info(f"    🛒 Visiting {deal.planszeo_url} for Planszeo details...")
        try:
            resp = self.session.get(str(deal.planszeo_url), timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            bgg_link = None
            bgg_a = soup.find('a', href=re.compile(r'boardgamegeek.com/boardgame/'))
            if bgg_a and 'href' in bgg_a.attrs:
                bgg_link = bgg_a['href']
            
            deal.bgg_url = bgg_link
            
            rank_div = soup.find('div', class_='inline-flex items-center rounded-md bg-gray-purple-800/20 px-2 py-1 text-lg font-bold text-gray-purple-800 ring-1 ring-inset ring-gray-purple-800/50')
            if rank_div:
                rank_text = rank_div.find('div').get_text(strip=True)
                if rank_text:
                    deal.planszeo_rank = int(rank_text.split('.')[0])

            rating_span = soup.find('span', class_='inline-flex items-center rounded-md bg-green-600/20 px-2 py-1 text-lg lg:text-xl font-bold text-green-600 ring-1 ring-inset ring-green-600/50')
            if rating_span:
                deal.planszeo_rating = float(rating_span.get_text(strip=True))

            if rating_span:
                rating_count_div = rating_span.find_parent('div').find_next_sibling('div', class_='text-xs')
                if rating_count_div:
                    rating_count_text = rating_count_div.get_text(strip=True).split(' ')[0]
                    if rating_count_text.isdigit():
                        deal.planszeo_rating_count = int(rating_count_text)

        except requests.exceptions.RequestException as e:
            logger.error(f"      Could not fetch Planszeo game details: {e}")
        except Exception as e:
            logger.error(f"      An error occurred while getting Planszeo game details: {e}")
        return deal
