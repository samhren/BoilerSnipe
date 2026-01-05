from pydantic_settings import BaseSettings
from typing import Optional, List
from pydantic import field_validator


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./purdue_courses.db"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: Optional[str] = None

    # Proxy (optional)
    PROXY_URL: Optional[str] = None

    # Scraper settings
    INVENTORY_CRON: str = "0 2 * * *"  # Daily at 2 AM
    SNIPER_INTERVAL_MINUTES: float = 5

    # CORS
    FRONTEND_URL: Optional[str] = None
    
    # Security
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
