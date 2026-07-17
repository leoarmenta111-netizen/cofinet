from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "CofiNet+ API"

    VERSION: str = "1.0.0"

    DEBUG: bool = True

    MERCADOPAGO_ACCESS_TOKEN: str | None = None

    MERCADOPAGO_PUBLIC_KEY: str | None = None

    FRONTEND_URL: str = "http://localhost:5500"
    MEMBERSHIP_WEBHOOK_URL: str | None = None


settings = Settings()
