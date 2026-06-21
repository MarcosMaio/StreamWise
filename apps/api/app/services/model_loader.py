import json
import logging
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.embedding import ModelVersion

logger = logging.getLogger(__name__)


class ModelLoader:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    async def get_active_version(self) -> ModelVersion | None:
        result = await self.db.execute(
            select(ModelVersion).where(ModelVersion.is_active.is_(True)).limit(1)
        )
        return result.scalar_one_or_none()

    async def is_model_available(self) -> bool:
        version = await self.get_active_version()
        if version is None:
            return False
        artifact = self.resolve_artifact_path(version.path)
        return artifact.exists()

    def resolve_artifact_path(self, path: str) -> Path:
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate
        repo_root = Path(__file__).resolve().parents[4]
        return repo_root / candidate

    @lru_cache(maxsize=1)
    def _load_item_embeddings_cached(self, artifact_path: str) -> dict[int, list[float]] | None:
        path = Path(artifact_path) / "item_embeddings.json"
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text())
            return {int(key): value for key, value in payload.items()}
        except Exception:
            logger.exception("Failed to load item embeddings from %s", path)
            return None

    def load_item_embeddings(self, version: ModelVersion) -> dict[int, list[float]] | None:
        artifact = self.resolve_artifact_path(version.path)
        return self._load_item_embeddings_cached(str(artifact))
