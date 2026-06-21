"""Offline recommendation baselines for MovieLens holdout evaluation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class EvalSplit:
    train_likes: dict[int, set[int]]
    test_relevant: dict[int, set[int]]
    user_seen: dict[int, set[int]]


def build_holdout_split(
    ratings: pd.DataFrame,
    *,
    positive_threshold: float = 4.0,
    min_train_likes: int = 5,
) -> EvalSplit:
    """Hold out the most recent positive interaction per eligible user."""
    positives = ratings[ratings["rating"] >= positive_threshold].copy()
    positives = positives.sort_values(["userId", "timestamp"])

    train_likes: dict[int, set[int]] = {}
    test_relevant: dict[int, set[int]] = {}
    user_seen: dict[int, set[int]] = defaultdict(set)

    for user_id, user_ratings in ratings.groupby("userId"):
        user_seen[int(user_id)] = set(user_ratings["movieId"].astype(int).tolist())

    for user_id, group in positives.groupby("userId"):
        items = group["movieId"].astype(int).tolist()
        if len(items) <= min_train_likes:
            continue
        train_likes[int(user_id)] = set(items[:-1])
        test_relevant[int(user_id)] = {items[-1]}

    return EvalSplit(train_likes=train_likes, test_relevant=test_relevant, user_seen=dict(user_seen))


class PopularityBaseline:
    name = "popularity"

    def __init__(self) -> None:
        self._item_scores: dict[int, float] = {}

    def fit(self, ratings: pd.DataFrame, positive_threshold: float = 4.0) -> None:
        positives = ratings[ratings["rating"] >= positive_threshold]
        counts = positives["movieId"].astype(int).value_counts()
        self._item_scores = {int(item_id): float(count) for item_id, count in counts.items()}

    def recommend(
        self,
        user_id: int,
        *,
        exclude: set[int],
        k: int = 10,
    ) -> list[int]:
        ranked = sorted(
            (
                (score, item_id)
                for item_id, score in self._item_scores.items()
                if item_id not in exclude
            ),
            reverse=True,
        )
        return [item_id for _, item_id in ranked[:k]]


class ContentOnlyBaseline:
    name = "content_only"

    def __init__(self) -> None:
        self._item_genres: dict[int, set[str]] = {}

    def fit(self, movies: pd.DataFrame) -> None:
        for row in movies.itertuples(index=False):
            movie_id = int(row.movieId)
            raw_genres = str(getattr(row, "genres", "") or "")
            if raw_genres in {"", "(no genres listed)"}:
                self._item_genres[movie_id] = set()
                continue
            self._item_genres[movie_id] = set(raw_genres.split("|"))

    def recommend(
        self,
        user_id: int,
        *,
        train_items: set[int],
        exclude: set[int],
        k: int = 10,
    ) -> list[int]:
        if not train_items:
            return []

        profile_genres: set[str] = set()
        for item_id in train_items:
            profile_genres.update(self._item_genres.get(item_id, set()))
        if not profile_genres:
            return []

        ranked: list[tuple[float, int]] = []
        for item_id, genres in self._item_genres.items():
            if item_id in exclude or not genres:
                continue
            overlap = len(profile_genres.intersection(genres))
            if overlap == 0:
                continue
            union = len(profile_genres.union(genres))
            score = overlap / union if union else 0.0
            ranked.append((score, item_id))

        ranked.sort(reverse=True)
        return [item_id for _, item_id in ranked[:k]]


class TwoTowerBaseline:
    name = "two_tower"

    def __init__(self) -> None:
        self._item_vectors: dict[int, np.ndarray] = {}

    def fit(self, embeddings_path) -> None:
        import json
        from pathlib import Path

        path = Path(embeddings_path)
        if not path.exists():
            return

        payload = json.loads(path.read_text())
        self._item_vectors = {
            int(item_id): np.array(vector, dtype=np.float32)
            for item_id, vector in payload.items()
        }

    @property
    def is_available(self) -> bool:
        return bool(self._item_vectors)

    def recommend(
        self,
        user_id: int,
        *,
        train_items: set[int],
        exclude: set[int],
        k: int = 10,
    ) -> list[int]:
        if not self._item_vectors or not train_items:
            return []

        vectors = [
            self._item_vectors[item_id]
            for item_id in train_items
            if item_id in self._item_vectors
        ]
        if not vectors:
            return []

        profile = np.mean(np.stack(vectors, axis=0), axis=0)
        profile_norm = np.linalg.norm(profile)
        if profile_norm == 0:
            return []

        profile = profile / profile_norm

        ranked: list[tuple[float, int]] = []
        for item_id, vector in self._item_vectors.items():
            if item_id in exclude:
                continue
            vector_norm = np.linalg.norm(vector)
            if vector_norm == 0:
                continue
            score = float(np.dot(profile, vector / vector_norm))
            ranked.append((score, item_id))

        ranked.sort(reverse=True)
        return [item_id for _, item_id in ranked[:k]]
