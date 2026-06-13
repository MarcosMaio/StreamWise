from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "StreamWise API"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://streamwise:streamwise@localhost:5432/streamwise"
    tmdb_api_key: str = ""
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    model_path: str = "ml/artifacts/two_tower/v1"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    google_client_id: str = ""
    google_client_secret: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
