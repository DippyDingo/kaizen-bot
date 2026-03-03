from pydantic_settings import BaseSettings
from pathlib import Path

# Путь к корню проекта (папка выше чем bot/)
BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    # Telegram
    bot_token: str

    # База данных
    database_url: str
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "second_brain"
    db_user: str = "postgres"
    db_password: str = "postgres"

    # Django
    secret_key: str = "dev-secret-key"
    debug: bool = True

    # Claude API
    claude_api_key: str = ""

    # Окружение
    environment: str = "development"

    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()