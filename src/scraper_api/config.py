from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    discord_api_secret: str
    log_level: str = "INFO"
    scraper_max_items: int = 100
    scraper_job_ttl: int = 3600
    scraper_user_agent: str = "discord-api-scraper/1.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
