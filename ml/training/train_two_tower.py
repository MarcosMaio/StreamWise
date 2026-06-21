#!/usr/bin/env python3
"""Train Two-Tower model on MovieLens ratings and register model version."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_config(path: Path) -> dict:
    with path.open() as handle:
        return yaml.safe_load(handle)


def build_training_pairs(ratings: pd.DataFrame, config: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    positive_threshold = config["data"]["positive_threshold"]
    negative_threshold = config["data"]["negative_threshold"]

    labels = []
    users = []
    items = []
    for row in ratings.itertuples(index=False):
        if row.rating >= positive_threshold:
            label = 1.0
        elif row.rating <= negative_threshold:
            label = 0.0
        else:
            continue
        users.append(int(row.userId))
        items.append(int(row.movieId))
        labels.append(label)

    return (
        np.array(users, dtype=np.int32),
        np.array(items, dtype=np.int32),
        np.array(labels, dtype=np.float32),
    )


def export_item_embedding_table(model, item_ids: np.ndarray, output_path: Path) -> None:
    import tensorflow as tf

    from two_tower_model import extract_item_embeddings

    embedding_layer = extract_item_embeddings(model)
    unique_items = np.unique(item_ids)
    vectors = embedding_layer(unique_items).numpy()
    payload = {
        str(int(item_id)): vectors[index].tolist()
        for index, item_id in enumerate(unique_items)
    }
    output_path.write_text(json.dumps(payload))
    logger.info("Saved %d item embeddings to %s", len(payload), output_path)


async def register_model_version(version: str, artifact_dir: Path, metrics: dict) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.models.embedding import ModelVersion

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        from sqlalchemy import update

        await session.execute(update(ModelVersion).values(is_active=False))
        session.add(
            ModelVersion(
                version=version,
                path=str(artifact_dir),
                is_active=True,
                trained_at=datetime.now(UTC).replace(tzinfo=None),
                metrics=metrics,
            )
        )
        await session.commit()
    await engine.dispose()


def main() -> None:
    import tensorflow as tf

    from two_tower_model import build_two_tower_model

    parser = argparse.ArgumentParser(description="Train StreamWise Two-Tower model")
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.yaml"))
    args = parser.parse_args()

    config = load_config(args.config)
    data_dir = Path(config["data"]["movielens_dir"])
    ratings_path = data_dir / "ratings.parquet"
    if not ratings_path.exists():
        raise SystemExit(f"Missing {ratings_path}. Run import_movielens.py first.")

    ratings = pd.read_parquet(ratings_path)
    users, items, labels = build_training_pairs(ratings, config)

    user_vocab = int(users.max()) + 1
    item_vocab = int(items.max()) + 1
    model = build_two_tower_model(
        user_vocab_size=max(user_vocab, config["model"]["user_vocab_size"]),
        item_vocab_size=max(item_vocab, config["model"]["item_vocab_size"]),
        embedding_dim=config["model"]["embedding_dim"],
    )

    history = model.fit(
        [users, items],
        labels,
        batch_size=config["training"]["batch_size"],
        epochs=config["training"]["epochs"],
        validation_split=config["training"]["validation_split"],
        verbose=1,
    )

    artifact_dir = Path(config["export"]["artifact_dir"])
    artifact_dir.mkdir(parents=True, exist_ok=True)
    model.save(artifact_dir / "model.keras")
    export_item_embedding_table(model, items, artifact_dir / "item_embeddings.json")

    metrics = {
        "loss": float(history.history["loss"][-1]),
        "auc": float(history.history.get("auc", [0.0])[-1]),
        "val_loss": float(history.history.get("val_loss", [0.0])[-1]),
        "training_pairs": int(len(labels)),
    }
    (artifact_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))

    asyncio.run(register_model_version(config["export"]["model_version"], artifact_dir, metrics))
    logger.info("Training complete. Artifact saved to %s", artifact_dir)


if __name__ == "__main__":
    main()
