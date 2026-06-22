import csv
import io
import uuid
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interaction import Interaction
from app.models.title import Title


class ImportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def import_watchlist_csv(self, user_id: UUID, csv_content: str) -> dict:
        reader = csv.DictReader(io.StringIO(csv_content))
        if not reader.fieldnames:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="CSV must include a header row",
            )

        tmdb_column = self._find_column(reader.fieldnames, ("tmdb_id", "tmdbId", "id"))
        if tmdb_column is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="CSV must include a tmdb_id column",
            )

        imported = 0
        skipped = 0
        missing: list[int] = []

        for row in reader:
            raw_id = (row.get(tmdb_column) or "").strip()
            if not raw_id:
                skipped += 1
                continue
            try:
                tmdb_id = int(raw_id)
            except ValueError:
                skipped += 1
                continue

            title = (
                await self.db.execute(select(Title).where(Title.tmdb_id == tmdb_id))
            ).scalar_one_or_none()
            if title is None:
                missing.append(tmdb_id)
                continue

            existing = (
                await self.db.execute(
                    select(Interaction).where(
                        Interaction.user_id == user_id,
                        Interaction.title_id == title.id,
                        Interaction.event_type == "watchlist",
                    )
                )
            ).scalar_one_or_none()
            if existing:
                skipped += 1
                continue

            self.db.add(
                Interaction(
                    user_id=user_id,
                    title_id=title.id,
                    event_type="watchlist",
                )
            )
            imported += 1

        await self.db.commit()
        return {
            "imported": imported,
            "skipped": skipped,
            "missing_tmdb_ids": missing[:20],
        }

    @staticmethod
    def _find_column(fieldnames: list[str], candidates: tuple[str, ...]) -> str | None:
        normalized = {name.lower(): name for name in fieldnames}
        for candidate in candidates:
            if candidate.lower() in normalized:
                return normalized[candidate.lower()]
        return None
