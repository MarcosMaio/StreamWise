"""Lazy-loaded sentence-transformers encoder for 384-dim synopsis embeddings."""

from __future__ import annotations


class EmbeddingGenerator:
    VECTOR_DIM = 384

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. Install with: pip install '.[ml]'"
            ) from exc

        self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def model(self):
        if self._model is None:
            return self._load_model()
        return self._model

    def encode(self, text: str) -> list[float]:
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("Cannot embed empty text")

        vector = self.model.encode(cleaned, normalize_embeddings=True)
        values = vector.tolist()
        if len(values) != self.VECTOR_DIM:
            raise ValueError(f"Expected {self.VECTOR_DIM}-dim vector, got {len(values)}")
        return values

    @staticmethod
    def build_title_text(title: str, overview: str | None, genres: list[str] | None = None) -> str:
        parts = [title.strip()]
        if genres:
            parts.append("Genres: " + ", ".join(genres))
        if overview and overview.strip():
            parts.append(overview.strip())
        return "\n".join(parts)
