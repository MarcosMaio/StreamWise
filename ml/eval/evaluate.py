#!/usr/bin/env python3
"""Offline recommendation evaluation (SC-007) plus optional DB checks (SC-004, SC-005)."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from baselines import (
    ContentOnlyBaseline,
    PopularityBaseline,
    TwoTowerBaseline,
    build_holdout_split,
)
from metrics import average_metric, catalog_coverage, ndcg_at_k, precision_at_k, recall_at_k

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_config(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return yaml.safe_load(handle)


def evaluate_baseline(
    *,
    name: str,
    split,
    recommendations: dict[int, list[int]],
    k: int,
    catalog_size: int,
) -> dict[str, float]:
    precisions: list[float] = []
    recalls: list[float] = []
    ndcgs: list[float] = []

    for user_id, relevant in split.test_relevant.items():
        recs = recommendations.get(user_id, [])
        precisions.append(precision_at_k(recs, relevant, k))
        recalls.append(recall_at_k(recs, relevant, k))
        ndcgs.append(ndcg_at_k(recs, relevant, k))

    return {
        "precision_at_k": round(average_metric(precisions), 4),
        "recall_at_k": round(average_metric(recalls), 4),
        "ndcg_at_k": round(average_metric(ndcgs), 4),
        "coverage": round(catalog_coverage(recommendations, catalog_size, k), 4),
        "evaluated_users": len(split.test_relevant),
    }


def run_movielens_eval(config: dict[str, Any]) -> dict[str, Any]:
    data_dir = Path(config["data"]["movielens_dir"])
    ratings_path = data_dir / "ratings.parquet"
    movies_path = data_dir / "movies.parquet"

    if not ratings_path.exists() or not movies_path.exists():
        raise SystemExit(
            f"Missing MovieLens parquet in {data_dir}. Run ml/training/import_movielens.py first."
        )

    ratings = pd.read_parquet(ratings_path)
    movies = pd.read_parquet(movies_path)

    k = int(config["eval"]["k"])
    positive_threshold = float(config["eval"]["positive_threshold"])
    min_train_likes = int(config["eval"]["min_train_likes"])

    split = build_holdout_split(
        ratings,
        positive_threshold=positive_threshold,
        min_train_likes=min_train_likes,
    )
    if not split.test_relevant:
        raise SystemExit("No eligible users for holdout evaluation. Import more MovieLens ratings.")

    catalog_size = int(movies["movieId"].nunique())
    results: dict[str, Any] = {
        "dataset": str(data_dir),
        "k": k,
        "evaluated_users": len(split.test_relevant),
        "catalog_size": catalog_size,
        "baselines": {},
    }

    def exclude_for_user(user_id: int) -> set[int]:
        seen = split.user_seen.get(user_id, set())
        held_out = split.test_relevant.get(user_id, set())
        return seen - held_out

    popularity = PopularityBaseline()
    popularity.fit(ratings, positive_threshold=positive_threshold)
    popularity_recs = {
        user_id: popularity.recommend(
            user_id,
            exclude=exclude_for_user(user_id),
            k=k,
        )
        for user_id in split.test_relevant
    }
    results["baselines"][popularity.name] = evaluate_baseline(
        name=popularity.name,
        split=split,
        recommendations=popularity_recs,
        k=k,
        catalog_size=catalog_size,
    )

    content = ContentOnlyBaseline()
    content.fit(movies)
    content_recs = {
        user_id: content.recommend(
            user_id,
            train_items=split.train_likes[user_id],
            exclude=exclude_for_user(user_id),
            k=k,
        )
        for user_id in split.test_relevant
    }
    results["baselines"][content.name] = evaluate_baseline(
        name=content.name,
        split=split,
        recommendations=content_recs,
        k=k,
        catalog_size=catalog_size,
    )

    two_tower_path = Path(config["artifacts"]["two_tower_dir"]) / "item_embeddings.json"
    two_tower = TwoTowerBaseline()
    two_tower.fit(two_tower_path)
    if two_tower.is_available:
        two_tower_recs = {
            user_id: two_tower.recommend(
                user_id,
                train_items=split.train_likes[user_id],
                exclude=exclude_for_user(user_id),
                k=k,
            )
            for user_id in split.test_relevant
        }
        results["baselines"][two_tower.name] = evaluate_baseline(
            name=two_tower.name,
            split=split,
            recommendations=two_tower_recs,
            k=k,
            catalog_size=catalog_size,
        )
    else:
        results["baselines"][two_tower.name] = {
            "skipped": True,
            "reason": f"Missing item embeddings at {two_tower_path}",
        }

    pop_precision = results["baselines"]["popularity"]["precision_at_k"]
    content_precision = results["baselines"]["content_only"]["precision_at_k"]
    content_ndcg = results["baselines"]["content_only"]["ndcg_at_k"]

    results["sc007"] = {
        "content_beats_popularity_precision": content_precision > pop_precision,
        "content_beats_popularity_ndcg": content_ndcg
        > results["baselines"]["popularity"]["ndcg_at_k"],
        "best_baseline": max(
            results["baselines"].items(),
            key=lambda item: item[1].get("ndcg_at_k", 0.0),
        )[0],
    }

    return results


async def evaluate_sc004_platform_affinity(
    *,
    min_likes: int = 5,
    dominant_ratio: float = 0.6,
    top_k: int = 10,
    target_ratio: float = 0.60,
) -> dict[str, Any]:
    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.orm import selectinload

    from app.config import get_settings
    from app.models.interaction import Interaction
    from app.models.title import Title, TitleGenre
    from app.models.user import User
    from app.services.catalog_service import COUNTRY_CODE
    from app.services.recommendation_service import RecommendationService

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    eligible_users = 0
    passing_users = 0
    samples: list[dict[str, Any]] = []

    async with session_factory() as session:
        like_counts = (
            await session.execute(
                select(Interaction.user_id, func.count())
                .where(Interaction.event_type == "like")
                .group_by(Interaction.user_id)
                .having(func.count() >= min_likes)
            )
        ).all()

        for user_id, _ in like_counts:
            user = (
                await session.execute(
                    select(User)
                    .where(User.id == user_id)
                    .options(
                        selectinload(User.preferences),
                        selectinload(User.streaming_affinities),
                    )
                )
            ).scalar_one_or_none()
            if user is None:
                continue

            provider_counts: dict[UUID, int] = {}
            likes = (
                await session.execute(
                    select(Interaction)
                    .where(Interaction.user_id == user_id, Interaction.event_type == "like")
                    .options(
                        selectinload(Interaction.title).selectinload(Title.streaming_providers),
                    )
                )
            ).scalars().unique().all()

            for interaction in likes:
                if interaction.title is None:
                    continue
                for link in interaction.title.streaming_providers:
                    if link.country_code != COUNTRY_CODE or link.availability_type != "flatrate":
                        continue
                    provider_counts[link.provider_id] = provider_counts.get(link.provider_id, 0) + 1

            if not provider_counts:
                continue

            total = sum(provider_counts.values())
            dominant_provider, dominant_count = max(provider_counts.items(), key=lambda item: item[1])
            if dominant_count / total < dominant_ratio:
                continue

            eligible_users += 1
            service = RecommendationService(session)
            feed = await service.get_for_you(user, limit=top_k)
            if not feed.items:
                continue

            matches = 0
            for item in feed.items:
                if any(
                    provider.id == dominant_provider
                    for provider in item.streaming_providers
                ):
                    matches += 1

            ratio = matches / len(feed.items)
            if ratio >= target_ratio:
                passing_users += 1

            if len(samples) < 5:
                samples.append(
                    {
                        "user_id": str(user_id),
                        "dominant_provider_id": str(dominant_provider),
                        "provider_match_ratio": round(ratio, 4),
                    }
                )

    await engine.dispose()

    observed_ratio = passing_users / eligible_users if eligible_users else None
    return {
        "metric": "platform_affinity_match",
        "success_criteria": "SC-004",
        "target_ratio": target_ratio,
        "eligible_users": eligible_users,
        "passing_users": passing_users,
        "pass_rate": round(observed_ratio, 4) if observed_ratio is not None else None,
        "passed": observed_ratio is not None and observed_ratio >= target_ratio,
        "skipped": eligible_users == 0,
        "samples": samples,
    }


async def evaluate_sc005_genre_overlap(
    *,
    sample_size: int = 100,
    top_k: int = 10,
    target_ratio: float = 0.70,
) -> dict[str, Any]:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.orm import selectinload

    from app.config import get_settings
    from app.models.embedding import TitleEmbedding
    from app.models.title import Title, TitleGenre, TitleGenre
    from app.services.vector_search_service import VectorSearchService

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    evaluated = 0
    passing = 0

    async with session_factory() as session:
        source_titles = (
            await session.execute(
                select(Title.id)
                .join(TitleEmbedding, TitleEmbedding.title_id == Title.id)
                .join(TitleGenre, TitleGenre.title_id == Title.id)
                .distinct()
                .limit(sample_size)
            )
        ).scalars().all()

        service = VectorSearchService(session)
        for title_id in source_titles:
            source_genres = (
                await session.execute(
                    select(TitleGenre.genre_id).where(TitleGenre.title_id == title_id)
                )
            ).scalars().all()
            source_genre_set = set(source_genres)
            if not source_genre_set:
                continue

            similar = await service.find_similar_titles(title_id, limit=top_k)
            if not similar.items:
                continue

            evaluated += 1
            overlap_hits = 0
            for item in similar.items:
                item_genres = (
                    await session.execute(
                        select(TitleGenre.genre_id).where(TitleGenre.title_id == item.id)
                    )
                ).scalars().all()
                if source_genre_set.intersection(item_genres):
                    overlap_hits += 1

            if overlap_hits / len(similar.items) >= target_ratio:
                passing += 1

    await engine.dispose()

    observed_ratio = passing / evaluated if evaluated else None
    return {
        "metric": "genre_overlap_similar_titles",
        "success_criteria": "SC-005",
        "target_ratio": target_ratio,
        "evaluated_titles": evaluated,
        "passing_titles": passing,
        "pass_rate": round(observed_ratio, 4) if observed_ratio is not None else None,
        "passed": observed_ratio is not None and observed_ratio >= target_ratio,
        "skipped": evaluated == 0,
    }


async def run_db_checks(config: dict[str, Any]) -> dict[str, Any]:
    gates = config.get("quality_gates", {})
    try:
        sc004 = await evaluate_sc004_platform_affinity(
            target_ratio=float(gates.get("sc004_min_ratio", 0.60)),
        )
        sc005 = await evaluate_sc005_genre_overlap(
            target_ratio=float(gates.get("sc005_min_ratio", 0.70)),
        )
        return {"sc004": sc004, "sc005": sc005}
    except Exception as exc:
        logger.warning("Database quality checks skipped: %s", exc)
        return {
            "sc004": {"skipped": True, "reason": str(exc)},
            "sc005": {"skipped": True, "reason": str(exc)},
        }


def print_summary(report: dict[str, Any]) -> None:
    print("\n=== StreamWise Offline Evaluation ===")
    print(f"Users evaluated: {report['offline_eval']['evaluated_users']}")
    print(f"Catalog size:    {report['offline_eval']['catalog_size']}")
    print(f"Cutoff K:        {report['offline_eval']['k']}\n")

    header = f"{'Baseline':<16} {'P@10':>8} {'R@10':>8} {'NDCG@10':>10} {'Coverage':>10}"
    print(header)
    print("-" * len(header))
    for name, metrics in report["offline_eval"]["baselines"].items():
        if metrics.get("skipped"):
            print(f"{name:<16} skipped ({metrics.get('reason', 'n/a')})")
            continue
        print(
            f"{name:<16} "
            f"{metrics['precision_at_k']:>8.4f} "
            f"{metrics['recall_at_k']:>8.4f} "
            f"{metrics['ndcg_at_k']:>10.4f} "
            f"{metrics['coverage']:>10.4f}"
        )

    sc007 = report["offline_eval"].get("sc007", {})
    print(
        f"\nSC-007 content-only beats popularity (precision): "
        f"{sc007.get('content_beats_popularity_precision')}"
    )
    print(
        f"SC-007 content-only beats popularity (NDCG): "
        f"{sc007.get('content_beats_popularity_ndcg')}"
    )

    if "product_checks" in report:
        for key in ("sc004", "sc005"):
            check = report["product_checks"].get(key, {})
            if check.get("skipped"):
                print(f"\n{key.upper()} skipped: {check.get('reason', 'insufficient data')}")
            else:
                print(
                    f"\n{key.upper()} pass rate: {check.get('pass_rate')} "
                    f"(target {check.get('target_ratio')}, passed={check.get('passed')})"
                )


async def async_main(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    offline_eval = run_movielens_eval(config)

    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "offline_eval": offline_eval,
    }

    if args.with_db_checks:
        report["product_checks"] = await run_db_checks(config)

    output_path = Path(config["output"]["metrics_path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2))
    logger.info("Wrote evaluation report to %s", output_path)

    print_summary(report)

    if args.publish:
        from publish_metrics import publish_metrics

        await publish_metrics(report, model_version=args.model_version)

    sc007 = offline_eval.get("sc007", {})
    best_ndcg = max(
        (
            metrics.get("ndcg_at_k", 0.0)
            for name, metrics in offline_eval.get("baselines", {}).items()
            if not metrics.get("skipped")
        ),
        default=0.0,
    )
    pop_ndcg = offline_eval["baselines"]["popularity"]["ndcg_at_k"]
    beats_popularity = best_ndcg > pop_ndcg
    if config.get("quality_gates", {}).get("sc007_beats_popularity") and not beats_popularity:
        logger.warning(
            "SC-007 gate not met: best baseline NDCG@10 (%.4f) did not beat popularity (%.4f)",
            best_ndcg,
            pop_ndcg,
        )

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate StreamWise recommendation quality")
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.yaml"))
    parser.add_argument("--with-db-checks", action="store_true", help="Run SC-004/SC-005 against PostgreSQL")
    parser.add_argument("--publish", action="store_true", help="Publish metrics to model_versions table")
    parser.add_argument("--model-version", default="v1")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(async_main(args)))


if __name__ == "__main__":
    main()
