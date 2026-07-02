"""Daily TMDB sync scheduler — runs at 06:00 UTC."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sync_catalog import STATUS_FILE, SyncRunResult, run_sync

try:
    from diff_catalog import run_diff
    from snapshot_providers import run_snapshot
except ImportError:
    run_snapshot = None
    run_diff = None

try:
    from jobs.email.weekly_digest import run_weekly_digest
except ImportError:
    try:
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from email.weekly_digest import run_weekly_digest
    except ImportError:
        run_weekly_digest = None

try:
    sys.path.insert(0, "/ml/training")
    from retrain_pipeline import run_pipeline as run_retrain_pipeline
except ImportError:
    run_retrain_pipeline = None

RETRAIN_INTERACTION_THRESHOLD = int(os.environ.get("RETRAIN_INTERACTION_THRESHOLD", "500"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

STATUS_DIR = Path(os.environ.get("SYNC_STATUS_DIR", Path(__file__).resolve().parent))
STATUS_DIR.mkdir(parents=True, exist_ok=True)
SCHEDULER_STATUS_FILE = STATUS_DIR / "scheduler_status.json"
_run_history: list[dict] = []


def _record_run(result: SyncRunResult) -> None:
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "success": result.success,
        "titles_synced": result.titles_synced,
        "providers_synced": result.providers_synced,
        "duration_seconds": result.duration_seconds,
        "error_count": len(result.errors),
    }
    _run_history.append(entry)
    _run_history[:] = _run_history[-30:]

    success_rate = sum(1 for r in _run_history if r["success"]) / len(_run_history)
    status = {
        "last_run": entry,
        "recent_runs": _run_history,
        "success_rate": round(success_rate, 4),
        "total_runs": len(_run_history),
        "last_sync_status_file": str(STATUS_FILE),
    }
    SCHEDULER_STATUS_FILE.write_text(json.dumps(status, indent=2))
    logger.info(
        "scheduler_health success_rate=%.1f%% runs=%d last_success=%s",
        success_rate * 100,
        len(_run_history),
        result.success,
    )


async def _interactions_since_last_retrain() -> int:
    """Count new interactions since the most recently trained model version."""
    import sys as _sys
    from pathlib import Path as _Path

    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2] / "apps" / "api"))

    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.models.embedding import ModelVersion
    from app.models.interaction import Interaction

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_factory() as session:
            trained_at = (
                await session.execute(
                    select(ModelVersion.trained_at).order_by(ModelVersion.trained_at.desc()).limit(1)
                )
            ).scalar_one_or_none()

            if trained_at is None:
                return RETRAIN_INTERACTION_THRESHOLD  # no model yet → trigger immediately

            count = (
                await session.execute(
                    select(func.count()).select_from(Interaction).where(Interaction.created_at > trained_at)
                )
            ).scalar() or 0
    finally:
        await engine.dispose()

    return count


def _scheduled_sync() -> None:
    import asyncio

    logger.info("Starting scheduled TMDB catalog sync")
    result = asyncio.run(run_sync())
    _record_run(result)
    if not result.success:
        logger.error("Scheduled sync failed: %s", result.errors)

    if run_snapshot and run_diff:
        asyncio.run(run_snapshot())
        asyncio.run(run_diff())

    try:
        new_interactions = asyncio.run(_interactions_since_last_retrain())
        logger.info(
            "Interactions since last retrain: %d (threshold=%d)",
            new_interactions,
            RETRAIN_INTERACTION_THRESHOLD,
        )
        if new_interactions >= RETRAIN_INTERACTION_THRESHOLD:
            logger.info("Interaction threshold reached — triggering retrain")
            _scheduled_retrain()
    except Exception as exc:
        logger.warning("Interaction threshold check failed: %s", exc)


def _scheduled_digest() -> None:
    import asyncio

    if run_weekly_digest is None:
        logger.warning("Weekly digest module unavailable")
        return
    logger.info("Starting weekly email digest")
    asyncio.run(run_weekly_digest())


def _scheduled_retrain() -> None:
    if run_retrain_pipeline is None:
        logger.warning("Retrain pipeline module unavailable")
        return

    logger.info("Starting weekly model retrain")
    try:
        run_retrain_pipeline(
            config_path=Path("/ml/training/config.yaml"),
            skip_import=False,
            skip_eval=True,
            skip_publish=True,
        )
    except Exception as exc:
        logger.exception("Weekly retrain failed: %s", exc)


def main() -> None:
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        _scheduled_sync,
        CronTrigger(hour=6, minute=0),
        id="tmdb_catalog_sync",
        name="TMDB daily catalog sync",
        replace_existing=True,
    )
    scheduler.add_job(
        _scheduled_digest,
        CronTrigger(day_of_week="sun", hour=8, minute=0),
        id="weekly_email_digest",
        name="Weekly recommendation digest",
        replace_existing=True,
    )
    scheduler.add_job(
        _scheduled_retrain,
        CronTrigger(day_of_week="sun", hour=7, minute=0),
        id="weekly_model_retrain",
        name="Weekly Two-Tower retrain",
        replace_existing=True,
    )

    logger.info("StreamWise scheduler started — daily sync 06:00 UTC, weekly retrain Sun 07:00 UTC")
    _scheduled_sync()
    scheduler.start()


if __name__ == "__main__":
    main()
