from sqlalchemy import Enum, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import AiRequestStatus, AiRequestType
from app.db.models.mixins import TimestampMixin


class AiRequests(Base, TimestampMixin):
    __tablename__ = "ai_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    request_type: Mapped[AiRequestType] = mapped_column(
        Enum(AiRequestType, name="ai_request_type"), nullable=False, default=AiRequestType.recipe_suggestion
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    pantry_snapshot_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[AiRequestStatus] = mapped_column(
        Enum(AiRequestStatus, name="ai_request_status"), nullable=False, default=AiRequestStatus.queued
    )
    result_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_ai_requests_user_created", "user_id", "created_at"),
        Index("idx_ai_requests_status_created", "status", "created_at"),
    )
