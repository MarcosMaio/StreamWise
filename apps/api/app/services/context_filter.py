from typing import Literal
from uuid import UUID

from app.models.title import Title
from app.schemas.context import SessionContext

MOOD_GENRES: dict[str, list[str]] = {
    "funny": ["Comedy"],
    "intense": ["Action", "Thriller", "Horror"],
    "cozy": ["Romance", "Family"],
    "thoughtful": ["Drama", "Documentary"],
}

COMPANY_GENRES: dict[str, list[str]] = {
    "family": ["Animation", "Family"],
    "date": ["Romance", "Comedy"],
}


def apply_session_context(candidates: list[Title], context: SessionContext | None) -> list[Title]:
    if context is None:
        return candidates

    filtered = candidates

    if context.time_budget == "short":
        filtered = [title for title in filtered if title.type == "movie"]
    elif context.time_budget == "long":
        filtered = [title for title in filtered if title.type == "series"]

    mood_genres = MOOD_GENRES.get(context.mood or "", [])
    if mood_genres:
        filtered = _filter_by_genre_names(filtered, mood_genres)

    company_genres = COMPANY_GENRES.get(context.company or "", [])
    if company_genres:
        filtered = _filter_by_genre_names(filtered, company_genres)

    return filtered if filtered else candidates


def _filter_by_genre_names(titles: list[Title], genre_names: list[str]) -> list[Title]:
    allowed = set(genre_names)
    matched = [
        title
        for title in titles
        if any(tg.genre and tg.genre.name in allowed for tg in title.title_genres)
    ]
    return matched


def mood_to_genre_names(mood: str | None) -> list[str]:
    if not mood:
        return []
    return MOOD_GENRES.get(mood, [])


def duration_to_title_type(duration: Literal["short", "long"] | None) -> str | None:
    if duration == "short":
        return "movie"
    if duration == "long":
        return "series"
    return None
