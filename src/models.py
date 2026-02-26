from typing import Optional
from pydantic import BaseModel, HttpUrl

class PlanszeoDeal(BaseModel):
    nazwa: str
    cena: float
    obnizka: str
    typ: str
    planszeo_url: HttpUrl
    planszeo_rating: Optional[float] = None
    planszeo_rating_count: Optional[int] = None
    planszeo_rank: Optional[int] = None
    bgg_url: Optional[HttpUrl] = None

class BggStats(BaseModel):
    bgg_rating: Optional[float] = None
    bgg_rank: Optional[int] = None

class GameDetails(PlanszeoDeal, BggStats):
    """Combined model for a game with both Planszeo and BGG data."""
    pass
