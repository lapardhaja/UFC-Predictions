from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    database_url: str = "sqlite:///./ufc.db"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    secret_key: str = "change-me"
    admin_api_key: str = "dev-admin-key-change-in-prod"
    mlflow_tracking_uri: str = "./mlruns"
    scrape_delay_min: float = 1.5
    scrape_delay_max: float = 3.0
    model_dir: Path = Path(__file__).resolve().parent.parent / "ml" / "models"


@lru_cache
def get_settings() -> Settings:
    return Settings()
