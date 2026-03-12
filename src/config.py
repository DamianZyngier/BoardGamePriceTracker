from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
from typing import Optional
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    BGG_API_TOKEN: SecretStr = Field(default=..., description="BGG Personal Access Token for API v2")
    EMAIL_SENDER: Optional[str] = Field(default=None, description="Gmail address for sending alerts")
    EMAIL_APP_PASSWORD: Optional[SecretStr] = Field(default=None, description="App Password for Gmail")
    EMAIL_RECEIVER: Optional[str] = Field(default=None)
    
    @property
    def receiver(self) -> str:
        return self.EMAIL_RECEIVER or self.EMAIL_SENDER or 'zyngi23@gmail.com'
    
    DATA_DIR: str = 'data'
    PLANSZEO_BASE_URL: str = "https://planszeo.pl"
    PLANSZEO_DEALS_URL: str = "https://planszeo.pl/okazje"
    
    # Request headers
    USER_AGENT: str = 'BoardGamePriceTracker/1.0 (https://github.com/zyngi/BoardGamePriceTracker)'

    @property
    def headers(self) -> dict:
        return {'User-Agent': self.USER_AGENT}

    @property
    def history_file(self) -> str:
        return os.path.join(self.DATA_DIR, 'game_history.json')

    @property
    def last_checked_file(self) -> str:
        return os.path.join(self.DATA_DIR, 'last_checked_games.json')

# Singleton instance
settings = Settings()

# Backward compatibility (optional, but good for transition)
class Config:
    BGG_API_TOKEN = settings.BGG_API_TOKEN.get_secret_value() if settings.BGG_API_TOKEN else None
    EMAIL_SENDER = settings.EMAIL_SENDER
    EMAIL_APP_PASSWORD = settings.EMAIL_APP_PASSWORD.get_secret_value() if settings.EMAIL_APP_PASSWORD else None
    EMAIL_RECEIVER = settings.receiver
    DATA_DIR = settings.DATA_DIR
    HISTORY_FILE = settings.history_file
    LAST_CHECKED_FILE = settings.last_checked_file
    PLANSZEO_BASE_URL = settings.PLANSZEO_BASE_URL
    PLANSZEO_DEALS_URL = settings.PLANSZEO_DEALS_URL
    HEADERS = settings.headers
