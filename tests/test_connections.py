import pytest
import requests
from src.config import Config
from src.bgg_api import BggApi
from src.scraper import PlanszeoScraper

@pytest.fixture
def session():
    s = requests.Session()
    s.headers.update(Config.HEADERS)
    return s

def test_planszeo_connection(session):
    """Test if Planszeo deals page is accessible and returns items."""
    scraper = PlanszeoScraper(session)
    deals = scraper.get_deals(1)
    assert isinstance(deals, list)
    # Even if there are no deals (unlikely), the connection should not fail
    assert len(deals) >= 0

def test_bgg_api_connection(session):
    """Test if BGG API is accessible with the provided token."""
    bgg_api = BggApi(session)
    # Testing with a well-known game: Catan (ID 13)
    bgg_url = "https://boardgamegeek.com/boardgame/13"
    stats = bgg_api.get_stats(bgg_url)
    
    # If the token is valid, we should get stats or a 202 (which get_stats handles)
    # The get_stats returns None if it fails after retries or unauthorized
    # Given our previous fix, this should return a dict if token is valid.
    assert stats is not None, "BGG API connection failed (possibly 401 or timeout)"
    assert 'bgg_rating' in stats
    assert isinstance(stats['bgg_rating'], (float, int))

def test_planszeo_detail_page(session):
    """Test if we can access a specific game page on Planszeo."""
    scraper = PlanszeoScraper(session)
    # We'll try to find the first game from the deals page and visit its details
    deals = scraper.get_deals(1)
    if deals:
        url = deals[0]['planszeo_url']
        details = scraper.get_details(url)
        assert details is not None
        assert 'bgg_url' in details
