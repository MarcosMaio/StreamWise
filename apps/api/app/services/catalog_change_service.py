import uuid
from datetime import date, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.p2 import CatalogProviderChange, ProviderAvailabilitySnapshot
from app.models.provider import StreamingProvider, TitleStreamingProvider
from app.models.title import Title
from app.services.catalog_service import COUNTRY_CODE


class CatalogChangeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def snapshot_current_providers(self, snapshot_date: date | None = None) -> int:
        snapshot_date = snapshot_date or date.today()
        await self.db.execute(
            delete(ProviderAvailabilitySnapshot).where(
                ProviderAvailabilitySnapshot.snapshot_date == snapshot_date
            )
        )

        result = await self.db.execute(select(TitleStreamingProvider))
        rows = result.scalars().all()
        for row in rows:
            if row.country_code != COUNTRY_CODE:
                continue
            self.db.add(
                ProviderAvailabilitySnapshot(
                    snapshot_date=snapshot_date,
                    title_id=row.title_id,
                    provider_id=row.provider_id,
                    availability_type=row.availability_type,
                    country_code=row.country_code,
                )
            )
        await self.db.commit()
        return len(rows)

    async def diff_snapshots(
        self,
        *,
        current_date: date | None = None,
        previous_date: date | None = None,
    ) -> int:
        current_date = current_date or date.today()
        previous_date = previous_date or date.fromordinal(current_date.toordinal() - 1)

        current = await self._load_snapshot_map(current_date)
        previous = await self._load_snapshot_map(previous_date)
        if not previous:
            return 0

        changes = 0
        now = datetime.utcnow()

        for key, (title_id, provider_id, availability_type) in current.items():
            if key not in previous:
                title_name, provider_name = await self._resolve_names(title_id, provider_id)
                self.db.add(
                    CatalogProviderChange(
                        id=uuid.uuid4(),
                        title_id=title_id,
                        provider_id=provider_id,
                        title_name=title_name,
                        provider_name=provider_name,
                        change_type="enter",
                        availability_type=availability_type,
                        detected_at=now,
                    )
                )
                changes += 1

        for key, (title_id, provider_id, availability_type) in previous.items():
            if key not in current:
                title_name, provider_name = await self._resolve_names(title_id, provider_id)
                self.db.add(
                    CatalogProviderChange(
                        id=uuid.uuid4(),
                        title_id=title_id,
                        provider_id=provider_id,
                        title_name=title_name,
                        provider_name=provider_name,
                        change_type="leave",
                        availability_type=availability_type,
                        detected_at=now,
                    )
                )
                changes += 1

        await self.db.commit()
        return changes

    async def list_recent_changes(self, *, limit: int = 20) -> list[CatalogProviderChange]:
        result = await self.db.execute(
            select(CatalogProviderChange)
            .order_by(CatalogProviderChange.detected_at.desc())
            .limit(min(limit, 50))
        )
        return list(result.scalars().all())

    async def _load_snapshot_map(self, snapshot_date: date) -> dict[tuple, tuple]:
        result = await self.db.execute(
            select(ProviderAvailabilitySnapshot).where(
                ProviderAvailabilitySnapshot.snapshot_date == snapshot_date,
                ProviderAvailabilitySnapshot.country_code == COUNTRY_CODE,
                ProviderAvailabilitySnapshot.availability_type == "flatrate",
            )
        )
        rows = result.scalars().all()
        return {
            (row.title_id, row.provider_id, row.availability_type): (
                row.title_id,
                row.provider_id,
                row.availability_type,
            )
            for row in rows
        }

    async def _resolve_names(self, title_id, provider_id) -> tuple[str, str]:
        title = await self.db.get(Title, title_id)
        provider = await self.db.get(StreamingProvider, provider_id)
        return (
            title.title if title else "Unknown title",
            provider.name if provider else "Unknown provider",
        )
