from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        extra="ignore"
    )

    APP_NAME: str = "CofiNet+ API"

    VERSION: str = "1.0.0"

    DEBUG: bool = False

    MERCADOPAGO_ACCESS_TOKEN: str | None = None
    MERCADOPAGO_PUBLIC_KEY: str | None = None

    FRONTEND_URL: str
    MEMBERSHIP_WEBHOOK_URL: str | None = None


settings = Settings()
