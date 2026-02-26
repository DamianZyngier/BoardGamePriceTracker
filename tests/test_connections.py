import pytest
import requests
from src.config import settings
from src.bgg_api import BggApi
from src.scraper import PlanszeoScraper
from src.models import PlanszeoDeal, BggStats

@pytest.fixture
def session():
    s = requests.Session()
    s.headers.update(settings.headers)
    return s

def test_planszeo_connection(session):
    """Test if Planszeo deals page is accessible and returns items."""
    scraper = PlanszeoScraper(session)
    deals = scraper.get_deals(1)
    assert isinstance(deals, list)
    if len(deals) > 0:
        assert isinstance(deals[0], PlanszeoDeal)

def test_bgg_api_connection(session):
    """Test if BGG API is accessible with the provided token."""
    bgg_api = BggApi(session)
    # Testing with a well-known game: Catan (ID 13)
    bgg_url = "https://boardgamegeek.com/boardgame/13"
    stats = bgg_api.get_stats(bgg_url)
    
    assert stats is not None
    assert isinstance(stats, BggStats)
    assert isinstance(stats.bgg_rating, (float, int))

def test_planszeo_detail_page(session):
    """Test if we can access a specific game page on Planszeo."""
    scraper = PlanszeoScraper(session)
    deals = scraper.get_deals(1)
    if deals:
        deal = deals[0]
        enriched_deal = scraper.get_details(deal)
        assert enriched_deal.planszeo_url is not None
        # Should have tried to find a BGG link
        assert hasattr(enriched_deal, 'bgg_url')
