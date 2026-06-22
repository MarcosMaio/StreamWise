"""Maximal Marginal Relevance reranking using genre overlap similarity."""

from __future__ import annotations

from app.models.title import Title


def _genre_set(title: Title) -> set[str]:
    return {tg.genre.name for tg in title.title_genres if tg.genre}


def genre_similarity(left: Title, right: Title) -> float:
    left_genres = _genre_set(left)
    right_genres = _genre_set(right)
    if not left_genres or not right_genres:
        return 0.0
    intersection = len(left_genres.intersection(right_genres))
    union = len(left_genres.union(right_genres))
    return intersection / union if union else 0.0


def mmr_rerank(
    ranked: list[tuple[float, Title]],
    *,
    limit: int,
    lambda_param: float = 0.7,
) -> list[tuple[float, Title]]:
    if not ranked or limit <= 0:
        return []

    lambda_param = max(0.0, min(1.0, lambda_param))
    pool = list(ranked)
    selected: list[tuple[float, Title]] = []

    while pool and len(selected) < limit:
        best_index = 0
        best_score = float("-inf")

        for index, (relevance, candidate) in enumerate(pool):
            if not selected:
                mmr_score = relevance
            else:
                max_sim = max(genre_similarity(candidate, chosen) for _, chosen in selected)
                mmr_score = lambda_param * relevance - (1.0 - lambda_param) * max_sim

            if mmr_score > best_score:
                best_score = mmr_score
                best_index = index

        selected.append(pool.pop(best_index))

    return selected


def genre_diversity_score(titles: list[Title]) -> float:
    """Unique genres in list divided by total genre slots (higher = more diverse)."""
    if not titles:
        return 0.0
    all_genres: set[str] = set()
    slots = 0
    for title in titles:
        genres = _genre_set(title)
        all_genres.update(genres)
        slots += max(len(genres), 1)
    return len(all_genres) / slots if slots else 0.0
