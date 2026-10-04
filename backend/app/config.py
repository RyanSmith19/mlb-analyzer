from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MLB_", extra="ignore")

    app_name: str = Field(default="MLB Pitch Matchup Analyzer", min_length=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
