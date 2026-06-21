"""Ranking metrics for offline recommendation evaluation."""

from __future__ import annotations

import math
from collections.abc import Iterable


def precision_at_k(recommended: Iterable[int], relevant: set[int], k: int = 10) -> float:
    top_k = list(recommended)[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for item_id in top_k if item_id in relevant)
    return hits / len(top_k)


def recall_at_k(recommended: Iterable[int], relevant: set[int], k: int = 10) -> float:
    if not relevant:
        return 0.0
    top_k = list(recommended)[:k]
    hits = sum(1 for item_id in top_k if item_id in relevant)
    return hits / len(relevant)


def ndcg_at_k(recommended: Iterable[int], relevant: set[int], k: int = 10) -> float:
    top_k = list(recommended)[:k]
    if not top_k or not relevant:
        return 0.0

    dcg = 0.0
    for index, item_id in enumerate(top_k):
        if item_id in relevant:
            dcg += 1.0 / math.log2(index + 2)

    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(index + 2) for index in range(ideal_hits))
    if idcg == 0:
        return 0.0
    return dcg / idcg


def catalog_coverage(all_recommendations: dict[int, list[int]], catalog_size: int, k: int = 10) -> float:
    if catalog_size <= 0:
        return 0.0
    recommended_items: set[int] = set()
    for items in all_recommendations.values():
        recommended_items.update(items[:k])
    return len(recommended_items) / catalog_size


def average_metric(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)
