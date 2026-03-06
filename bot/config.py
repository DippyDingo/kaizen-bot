from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    bot_token: str
    webapp_url: str = "https://example.com"
    api_host: str = "127.0.0.1"
    api_port: int = 8080

    database_url: str
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "second_brain"
    db_user: str = "postgres"
    db_password: str = "postgres"

    secret_key: str = "dev-secret-key"
    debug: bool = True

    claude_api_key: str = ""
    environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, bool):
            return value
        if value is None:
            return True

        text = str(value).strip().lower()
        truthy = {"1", "true", "yes", "on", "dev", "debug", "development"}
        falsy = {"0", "false", "no", "off", "prod", "production", "release"}

        if text in truthy:
            return True
        if text in falsy:
            return False

        raise ValueError("debug must be a boolean-like value")


settings = Settings()
