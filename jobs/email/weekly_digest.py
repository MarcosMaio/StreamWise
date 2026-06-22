#!/usr/bin/env python3
"""Send weekly recommendation digest emails (top 5 For You titles per user)."""

from __future__ import annotations

import asyncio
import logging
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Template
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from app.config import Settings, get_settings
from app.models.user import User
from app.services.recommendation_service import RecommendationService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "weekly_digest.html"


def _render_email(display_name: str, recommendations: list[dict]) -> str:
    template = Template(TEMPLATE_PATH.read_text())
    return template.render(display_name=display_name, recommendations=recommendations)


def _send_email(settings: Settings, to_email: str, html_body: str) -> None:
    if not settings.smtp_host:
        raise RuntimeError("SMTP_HOST is not configured")

    message = MIMEMultipart("alternative")
    message["Subject"] = "Your StreamWise weekly picks"
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as client:
        if settings.smtp_use_tls:
            client.starttls()
        if settings.smtp_user:
            client.login(settings.smtp_user, settings.smtp_password.get_secret_value())
        client.sendmail(settings.smtp_from, [to_email], message.as_string())


async def run_weekly_digest() -> dict:
    settings = get_settings()
    if not settings.smtp_host:
        logger.warning("SMTP not configured; skipping weekly digest")
        return {"sent": 0, "skipped": True}

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    sent = 0
    async with session_factory() as session:
        users = (
            await session.execute(
                select(User)
                .where(User.onboarding_complete.is_(True))
                .options(
                    selectinload(User.preferences),
                    selectinload(User.streaming_affinities),
                )
            )
        ).scalars().all()

        for user in users:
            service = RecommendationService(session)
            feed = await service.get_for_you(user, limit=5)
            if not feed.items:
                continue

            recommendations = [
                {"title": item.title, "genres": item.genres[:3]} for item in feed.items[:5]
            ]
            html = _render_email(user.display_name, recommendations)
            try:
                _send_email(settings, user.email, html)
                sent += 1
            except Exception as exc:
                logger.warning("Failed to send digest to %s: %s", user.email, exc)

    await engine.dispose()
    logger.info("Weekly digest sent to %d users", sent)
    return {"sent": sent, "skipped": False}


def main() -> None:
    asyncio.run(run_weekly_digest())


if __name__ == "__main__":
    main()
