"""SQLAlchemy ORM models."""

from app.models.embedding import ModelVersion, TitleEmbedding, UserEmbedding, UserStreamingAffinity
from app.models.interaction import Interaction, UserPreference, UserSeriesProgress
from app.models.provider import StreamingProvider, TitleStreamingProvider
from app.models.title import Genre, Title, TitleGenre
from app.models.user import OAuthAccount, User

__all__ = [
    "User",
    "OAuthAccount",
    "Genre",
    "Title",
    "TitleGenre",
    "StreamingProvider",
    "TitleStreamingProvider",
    "Interaction",
    "UserPreference",
    "UserSeriesProgress",
    "TitleEmbedding",
    "UserEmbedding",
    "UserStreamingAffinity",
    "ModelVersion",
]
