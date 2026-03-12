from typing import Optional
from pydantic import BaseModel, HttpUrl, ConfigDict

class PlanszeoDeal(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    
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
    model_config = ConfigDict(validate_assignment=True)
    
    bgg_rating: Optional[float] = None
    bgg_rank: Optional[int] = None

class GameDetails(PlanszeoDeal, BggStats):
    """Combined model for a game with both Planszeo and BGG data."""
    passed_threshold: bool = False
