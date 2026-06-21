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


def _scheduled_sync() -> None:
    import asyncio

    logger.info("Starting scheduled TMDB catalog sync")
    result = asyncio.run(run_sync())
    _record_run(result)
    if not result.success:
        logger.error("Scheduled sync failed: %s", result.errors)


def main() -> None:
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        _scheduled_sync,
        CronTrigger(hour=6, minute=0),
        id="tmdb_catalog_sync",
        name="TMDB daily catalog sync",
        replace_existing=True,
    )

    logger.info("StreamWise TMDB scheduler started — daily sync at 06:00 UTC")
    _scheduled_sync()
    scheduler.start()


if __name__ == "__main__":
    main()
