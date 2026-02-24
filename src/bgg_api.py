import requests
import xml.etree.ElementTree as ET
import time
import re
from typing import Optional, Dict, Any

from src.config import Config
from src.logger import setup_logger

logger = setup_logger(__name__)

class BggApi:
    def __init__(self, session: requests.Session):
        self.session = session

    def get_stats(self, bgg_url: str) -> Optional[Dict[str, Any]]:
        """Gets rating and rank from BGG using the XML API2."""
        if not bgg_url:
            return None
        
        match = re.search(r'/boardgame/(\d+)', bgg_url)
        if not match:
            return None
        
        bgg_id = match.group(1)
        api_url = f"https://boardgamegeek.com/xmlapi2/thing?id={bgg_id}&stats=1"
        logger.info(f"    🎲 Fetching BGG stats for ID {bgg_id}...")
        
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                headers = {}
                if Config.BGG_API_TOKEN:
                    headers['Authorization'] = f"Bearer {Config.BGG_API_TOKEN}"
                    
                resp = self.session.get(api_url, headers=headers, timeout=10)
                resp.raise_for_status()
                
                if resp.status_code == 202:
                    if attempt < max_retries:
                        logger.warning(f"      BGG processing (202), retrying in 3s... (Attempt {attempt+1}/{max_retries})")
                        time.sleep(3)
                        continue
                    else:
                        return None

                root = ET.fromstring(resp.content)
                item = root.find('item')
                if item is None:
                    return None
                
                stats_node = item.find('statistics')
                if stats_node is None: return None
                ratings_node = stats_node.find('ratings')
                if ratings_node is None: return None
                
                rating = ratings_node.find('average').get('value')
                
                bgg_rank = None
                ranks_node = ratings_node.find('ranks')
                if ranks_node is not None:
                    ranks = ranks_node.findall('rank')
                    for r in ranks:
                        if r.get('name') == 'boardgame':
                            rank_val = r.get('value')
                            if rank_val and rank_val.isdigit():
                                bgg_rank = int(rank_val)
                            break
                
                return {
                    'bgg_rating': float(rating) if rating else None,
                    'bgg_rank': bgg_rank
                }
            except Exception as e:
                logger.error(f"      Error fetching BGG stats: {e}")
                return None
        return None
