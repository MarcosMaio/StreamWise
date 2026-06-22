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

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_config(path: Path) -> dict:
    with path.open() as handle:
        return yaml.safe_load(handle)


def load_mlflow_config() -> dict:
    mlflow_config_path = REPO_ROOT / "ml/mlflow/config.yaml"
    if not mlflow_config_path.exists():
        return {}
    with mlflow_config_path.open() as handle:
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
    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.models.embedding import ModelVersion

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
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


def _setup_mlflow(mlflow_cfg: dict):
    import mlflow

    tracking_uri = mlflow_cfg.get("tracking_uri", "ml/artifacts/mlruns")
    tracking_path = REPO_ROOT / tracking_uri if not str(tracking_uri).startswith("file:") else Path(tracking_uri.replace("file:", ""))
    tracking_path.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(tracking_path.as_uri())
    mlflow.set_experiment(mlflow_cfg.get("experiment_name", "streamwise-two-tower"))
    return mlflow


def main() -> None:
    from two_tower_model import build_two_tower_model

    parser = argparse.ArgumentParser(description="Train StreamWise Two-Tower model")
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.yaml"))
    parser.add_argument("--ratings-path", type=Path, default=None)
    parser.add_argument("--artifact-dir", type=Path, default=None)
    parser.add_argument("--model-version", type=str, default=None)
    parser.add_argument("--disable-mlflow", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    data_dir = Path(config["data"]["movielens_dir"])
    if not data_dir.is_absolute():
        data_dir = REPO_ROOT / data_dir

    ratings_path = args.ratings_path or (data_dir / "ratings.parquet")
    if not ratings_path.is_absolute():
        ratings_path = REPO_ROOT / ratings_path

    if not ratings_path.exists():
        raise SystemExit(f"Missing {ratings_path}. Run import_movielens.py or retrain_pipeline.py first.")

    ratings = pd.read_parquet(ratings_path)
    users, items, labels = build_training_pairs(ratings, config)
    if len(labels) == 0:
        raise SystemExit("No training pairs after label filtering.")

    user_vocab = int(users.max()) + 1
    item_vocab = int(items.max()) + 1
    model = build_two_tower_model(
        user_vocab_size=max(user_vocab, config["model"]["user_vocab_size"]),
        item_vocab_size=max(item_vocab, config["model"]["item_vocab_size"]),
        embedding_dim=config["model"]["embedding_dim"],
    )

    mlflow_cfg = load_mlflow_config()
    mlflow = None
    run = None
    if not args.disable_mlflow and mlflow_cfg:
        try:
            mlflow = _setup_mlflow(mlflow_cfg)
            run = mlflow.start_run(run_name=args.model_version or config["export"]["model_version"])
            mlflow.log_params(
                {
                    "embedding_dim": config["model"]["embedding_dim"],
                    "batch_size": config["training"]["batch_size"],
                    "epochs": config["training"]["epochs"],
                    "training_pairs": len(labels),
                    "ratings_path": str(ratings_path),
                }
            )
        except Exception as exc:
            logger.warning("MLflow tracking unavailable: %s", exc)
            mlflow = None
            run = None

    history = model.fit(
        [users, items],
        labels,
        batch_size=config["training"]["batch_size"],
        epochs=config["training"]["epochs"],
        validation_split=config["training"]["validation_split"],
        verbose=1,
    )

    artifact_dir = args.artifact_dir or Path(config["export"]["artifact_dir"])
    if not artifact_dir.is_absolute():
        artifact_dir = REPO_ROOT / artifact_dir
    artifact_dir.mkdir(parents=True, exist_ok=True)

    model.save(artifact_dir / "model.keras")
    export_item_embedding_table(model, items, artifact_dir / "item_embeddings.json")

    metrics = {
        "loss": float(history.history["loss"][-1]),
        "auc": float(history.history.get("auc", [0.0])[-1]),
        "val_loss": float(history.history.get("val_loss", [0.0])[-1]),
        "training_pairs": int(len(labels)),
        "platform_merged": "platform" in ratings.columns and (ratings["source"] == "platform").any(),
    }
    (artifact_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))

    model_version = args.model_version or config["export"]["model_version"]
    asyncio.run(register_model_version(model_version, artifact_dir, metrics))

    if mlflow and run:
        try:
            mlflow.log_metrics(
                {
                    "loss": metrics["loss"],
                    "auc": metrics["auc"],
                    "val_loss": metrics["val_loss"],
                }
            )
            mlflow.log_artifact(str(artifact_dir / "metrics.json"))
            registered_name = mlflow_cfg.get("registered_model_name")
            if registered_name:
                mlflow.tensorflow.log_model(model, artifact_path="model", registered_model_name=registered_name)
            else:
                mlflow.tensorflow.log_model(model, artifact_path="model")
            mlflow.end_run()
        except Exception as exc:
            logger.warning("MLflow artifact logging failed: %s", exc)

    logger.info("Training complete. Artifact saved to %s", artifact_dir)


if __name__ == "__main__":
    main()
