from pydantic_settings import BaseSettings
from typing import Optional


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

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
