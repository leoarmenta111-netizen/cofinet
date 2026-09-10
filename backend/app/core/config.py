from pathlib import Path
from urllib.parse import quote

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Operational configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "production"
    APP_NAME: str = "CofiNet+ API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_HOST: str
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str
    DATABASE_USER: str
    DATABASE_PASSWORD: SecretStr

    JWT_SECRET_KEY: SecretStr = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, gt=0)

    CORS_ORIGINS: list[str] = Field(default_factory=list)
    FRONTEND_URL: str
    MEMBERSHIP_WEBHOOK_URL: str | None = None

    MERCADOPAGO_ACCESS_TOKEN: str | None = None
    MERCADOPAGO_PUBLIC_KEY: str | None = None

    @property
    def database_url(self) -> str:
        user = quote(self.DATABASE_USER, safe="")
        password = quote(self.DATABASE_PASSWORD.get_secret_value(), safe="")
        return (
            f"postgresql://{user}:{password}@{self.DATABASE_HOST}:"
            f"{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )


settings = Settings()
