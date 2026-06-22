from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_API_DIR = Path(__file__).resolve().parents[1]
_API_ENV = _API_DIR / ".env"

_SENSITIVE_FIELDS = frozenset(
    {
        "tmdb_api_key",
        "jwt_secret",
        "google_client_secret",
        "admin_api_key",
        "trakt_client_secret",
        "smtp_password",
    }
)


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
    cors_origins: str = "http://localhost:3000"
    rate_limit_enabled: bool = True
    rate_limit_auth_per_minute: int = 10
    rate_limit_search_per_minute: int = 30
    tmdb_api_key: SecretStr = SecretStr("")
    jwt_secret: SecretStr = SecretStr("change-me-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    model_path: str = "ml/artifacts/two_tower/v1"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    google_client_id: str = ""
    google_client_secret: SecretStr = SecretStr("")
    mmr_lambda: float = 0.7
    admin_api_key: SecretStr = SecretStr("")
    trakt_client_id: str = ""
    trakt_client_secret: SecretStr = SecretStr("")
    trakt_redirect_uri: str = "http://localhost:3000/profile/import"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from: str = "streamwise@localhost"
    smtp_use_tls: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def safe_display(self) -> dict[str, Any]:
        """Return settings with secrets redacted — safe for logs and debugging."""
        display: dict[str, Any] = {}
        for name in Settings.model_fields:
            value = getattr(self, name)
            if name in _SENSITIVE_FIELDS or isinstance(value, SecretStr):
                display[name] = "***"
            else:
                display[name] = value
        return display

    def __repr__(self) -> str:
        return f"Settings({self.safe_display()})"

    def __str__(self) -> str:
        return self.__repr__()


@lru_cache
def get_settings() -> Settings:
    return Settings()
