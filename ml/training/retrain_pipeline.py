#!/usr/bin/env python3
"""Merge MovieLens ratings with StreamWise platform interactions and retrain."""

from __future__ import annotations

import argparse
import asyncio
import logging
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_config(path: Path) -> dict:
    with path.open() as handle:
        return yaml.safe_load(handle)


async def export_platform_interactions(output_path: Path) -> int:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.orm import selectinload

    from app.config import get_settings
    from app.models.interaction import Interaction
    from app.models.title import Title

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    rows: list[dict] = []
    user_offset = 2_000_000

    async with session_factory() as session:
        result = await session.execute(
            select(Interaction)
            .join(Title, Title.id == Interaction.title_id)
            .where(Title.movielens_id.is_not(None))
            .options(selectinload(Interaction.title))
            .order_by(Interaction.created_at)
        )
        interactions = result.scalars().unique().all()
        user_map: dict[str, int] = {}

        for interaction in interactions:
            if interaction.title is None or interaction.title.movielens_id is None:
                continue

            user_key = str(interaction.user_id)
            if user_key not in user_map:
                user_map[user_key] = user_offset + len(user_map)

            rating_value = _interaction_to_rating(interaction.event_type, interaction.rating)
            if rating_value is None:
                continue

            rows.append(
                {
                    "userId": user_map[user_key],
                    "movieId": int(interaction.title.movielens_id),
                    "rating": rating_value,
                    "timestamp": int(interaction.created_at.timestamp()),
                    "source": "platform",
                }
            )

    await engine.dispose()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        pd.DataFrame(rows).to_parquet(output_path, index=False)
    else:
        pd.DataFrame(columns=["userId", "movieId", "rating", "timestamp", "source"]).to_parquet(
            output_path, index=False
        )

    logger.info("Exported %d platform interaction rows to %s", len(rows), output_path)
    return len(rows)


def _interaction_to_rating(event_type: str, rating: float | None) -> float | None:
    if event_type == "like":
        return 5.0
    if event_type == "dislike":
        return 1.0
    if event_type == "rating" and rating is not None:
        return float(rating)
    return None


def merge_ratings(
    movielens_path: Path,
    platform_path: Path,
    output_path: Path,
) -> pd.DataFrame:
    movielens = pd.read_parquet(movielens_path)
    movielens = movielens.assign(source="movielens")

    platform_count = 0
    platform = pd.DataFrame()
    if platform_path.exists():
        platform = pd.read_parquet(platform_path)
        platform_count = len(platform)

    if platform_count > 0:
        merged = pd.concat([movielens, platform], ignore_index=True)
    else:
        merged = movielens

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(output_path, index=False)
    logger.info(
        "Merged training set: %d MovieLens + %d platform = %d total rows",
        len(movielens),
        platform_count,
        len(merged),
    )
    return merged


def _run_step(command: list[str], *, cwd: Path | None = None) -> None:
    logger.info("Running: %s", " ".join(command))
    subprocess.run(command, check=True, cwd=cwd or REPO_ROOT)


def run_pipeline(
    *,
    config_path: Path,
    skip_import: bool = False,
    skip_eval: bool = False,
    skip_publish: bool = False,
) -> None:
    config = load_config(config_path)
    training_dir = Path(__file__).resolve().parent
    movielens_dir = REPO_ROOT / config["data"]["movielens_dir"]
    platform_path = REPO_ROOT / config["data"].get("platform_interactions_path", "ml/artifacts/platform/interactions.parquet")
    merged_path = REPO_ROOT / config["data"].get("merged_ratings_path", "ml/artifacts/training/ratings_merged.parquet")
    ratings_path = movielens_dir / "ratings.parquet"

    if not skip_import and not ratings_path.exists():
        logger.info("MovieLens ratings missing — running import_movielens.py")
        _run_step(
            [
                sys.executable,
                str(training_dir / "import_movielens.py"),
                "--output-dir",
                str(movielens_dir),
            ]
        )

    if not ratings_path.exists():
        raise SystemExit(f"Missing MovieLens ratings at {ratings_path}")

    platform_rows = asyncio.run(export_platform_interactions(platform_path))
    merge_ratings(ratings_path, platform_path, merged_path)

    version_suffix = datetime.now(UTC).strftime("%Y%m%d")
    artifact_dir = REPO_ROOT / config["export"]["artifact_dir"]
    if config["export"].get("versioned_artifacts", True):
        artifact_dir = artifact_dir.parent / f"{artifact_dir.name}-{version_suffix}"

    model_version = f"{config['export']['model_version']}-{version_suffix}"

    _run_step(
        [
            sys.executable,
            str(training_dir / "train_two_tower.py"),
            "--config",
            str(config_path),
            "--ratings-path",
            str(merged_path),
            "--artifact-dir",
            str(artifact_dir),
            "--model-version",
            model_version,
        ]
    )

    _run_step(
        [
            sys.executable,
            str(training_dir / "export_item_embeddings.py"),
            "--artifact-dir",
            str(artifact_dir),
        ]
    )

    if not skip_eval:
        eval_script = REPO_ROOT / "ml/eval/evaluate.py"
        if eval_script.exists():
            _run_step([sys.executable, str(eval_script), "--config", str(REPO_ROOT / "ml/eval/config.yaml")])

    if not skip_publish:
        eval_metrics = REPO_ROOT / "ml/artifacts/eval/metrics.json"
        if eval_metrics.exists():
            _run_step(
                [
                    sys.executable,
                    str(REPO_ROOT / "ml/eval/publish_metrics.py"),
                    "--metrics-file",
                    str(eval_metrics),
                    "--model-version",
                    model_version,
                ]
            )

    logger.info(
        "Retrain pipeline complete. model_version=%s platform_rows=%d artifact_dir=%s",
        model_version,
        platform_rows,
        artifact_dir,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="StreamWise retrain pipeline")
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.yaml"))
    parser.add_argument("--skip-import", action="store_true")
    parser.add_argument("--skip-eval", action="store_true")
    parser.add_argument("--skip-publish", action="store_true")
    args = parser.parse_args()
    run_pipeline(
        config_path=args.config,
        skip_import=args.skip_import,
        skip_eval=args.skip_eval,
        skip_publish=args.skip_publish,
    )


if __name__ == "__main__":
    main()
