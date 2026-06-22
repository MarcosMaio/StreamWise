from uuid import UUID

from app.models.title import Title
from app.services.catalog_service import COUNTRY_CODE


class ExplainabilityService:
    def build_reason_tags(
        self,
        title: Title,
        *,
        user_genre_names: set[str],
        affinities: dict[UUID, float],
        has_likes: bool,
        content_similarity: float | None = None,
    ) -> list[str]:
        tags: list[str] = []

        title_genres = {tg.genre.name for tg in title.title_genres if tg.genre}
        overlap = user_genre_names.intersection(title_genres)
        if overlap:
            genre = sorted(overlap)[0]
            tags.append(f"Matches your {genre} taste")

        if title.is_trending:
            tags.append("Trending now")

        provider_names = self._affinity_provider_names(title, affinities)
        if provider_names:
            tags.append(f"On {provider_names[0]}")

        if has_likes and content_similarity is not None and content_similarity >= 0.65:
            tags.append("Similar to titles you liked")

        return tags[:3]

    def _affinity_provider_names(
        self,
        title: Title,
        affinities: dict[UUID, float],
    ) -> list[str]:
        if not affinities:
            return []

        scored: list[tuple[float, str]] = []
        for link in title.streaming_providers:
            if link.country_code != COUNTRY_CODE or link.availability_type != "flatrate":
                continue
            if link.provider_id not in affinities or link.provider is None:
                continue
            scored.append((affinities[link.provider_id], link.provider.name))

        scored.sort(reverse=True)
        return [name for _, name in scored]
