from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_API_DIR = Path(__file__).resolve().parents[1]
_API_ENV = _API_DIR / ".env"


def _find_infra_env() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "infra" / ".env"
        if candidate.is_file():
            return candidate
    return None


def _resolve_env_files() -> tuple[str, ...]:
    """Load shared infra/.env first, then apps/api/.env overrides (local dev)."""
    files: list[str] = []
    infra_env = _find_infra_env()
    if infra_env:
        files.append(str(infra_env))
    if _API_ENV.exists():
        files.append(str(_API_ENV))
    return tuple(files) if files else (".env",)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_resolve_env_files(),
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
    mmr_lambda: float = 0.7
    admin_api_key: str = ""
    trakt_client_id: str = ""
    trakt_client_secret: str = ""
    trakt_redirect_uri: str = "http://localhost:3000/profile/import"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "streamwise@localhost"
    smtp_use_tls: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
