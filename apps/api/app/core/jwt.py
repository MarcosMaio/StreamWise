from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from jose import JWTError, jwt

from app.config import Settings


def create_access_token(subject: UUID, settings: Settings) -> str:
    return _create_token(
        subject,
        settings,
        expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
        token_type="access",
    )


def create_refresh_token(subject: UUID, settings: Settings) -> str:
    return _create_token(
        subject,
        settings,
        expires_delta=timedelta(days=30),
        token_type="refresh",
    )


def decode_token(token: str, settings: Settings) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.jwt_secret.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
    )


def get_token_subject(token: str, settings: Settings) -> UUID:
    try:
        payload = decode_token(token, settings)
    except JWTError as exc:
        raise ValueError("Invalid token") from exc

    if payload.get("type") != "access":
        raise ValueError("Invalid token type")

    subject = payload.get("sub")
    if not subject:
        raise ValueError("Invalid token subject")

    return UUID(subject)


def _create_token(
    subject: UUID,
    settings: Settings,
    *,
    expires_delta: timedelta,
    token_type: str,
) -> str:
    expire = datetime.now(UTC) + expires_delta
    payload = {
        "sub": str(subject),
        "exp": expire,
        "type": token_type,
    }
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm)
