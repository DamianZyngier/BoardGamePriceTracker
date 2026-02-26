import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BGG_API_TOKEN = os.environ.get('BGG_API_TOKEN')
    EMAIL_SENDER = os.environ.get('EMAIL_SENDER')
    EMAIL_APP_PASSWORD = os.environ.get('EMAIL_APP_PASSWORD')
    EMAIL_RECEIVER = 'zyngi23@gmail.com'
    DATA_DIR = 'data'
    HISTORY_FILE = os.path.join(DATA_DIR, 'game_history.json')
    LAST_CHECKED_FILE = os.path.join(DATA_DIR, 'last_checked_games.json')
    
    # Planszeo URLs
    PLANSZEO_BASE_URL = "https://planszeo.pl"
    PLANSZEO_DEALS_URL = "https://planszeo.pl/okazje"

    # Request headers
    HEADERS = {
        'User-Agent': 'BoardGamePriceTracker/1.0 (https://github.com/zyngi/BoardGamePriceTracker)'
    }
