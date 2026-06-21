#!/usr/bin/env python3
"""Merge offline evaluation metrics into the active model_versions row."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def publish_metrics(report: dict[str, Any], *, model_version: str = "v1") -> None:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.models.embedding import ModelVersion

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        result = await session.execute(
            select(ModelVersion).where(ModelVersion.version == model_version)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise SystemExit(f"Model version '{model_version}' not found in model_versions")

        merged = dict(model.metrics or {})
        merged["offline_eval"] = report.get("offline_eval", report)
        if "product_checks" in report:
            merged["product_checks"] = report["product_checks"]
        merged["eval_generated_at"] = report.get("generated_at")

        model.metrics = merged
        await session.commit()
        logger.info("Updated metrics for model version %s", model_version)

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish eval metrics to model_versions")
    parser.add_argument(
        "--metrics-file",
        type=Path,
        default=Path("ml/artifacts/eval/metrics.json"),
    )
    parser.add_argument("--model-version", default="v1")
    args = parser.parse_args()

    if not args.metrics_file.exists():
        raise SystemExit(f"Metrics file not found: {args.metrics_file}")

    report = json.loads(args.metrics_file.read_text())
    asyncio.run(publish_metrics(report, model_version=args.model_version))


if __name__ == "__main__":
    main()
