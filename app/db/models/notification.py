import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import DeliveryChannel, NotificationStatus, NotificationType
from app.db.models.mixins import SoftDeleteMixin, TimestampMixin


class Notifications(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType, name="notification_type"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    delivery_channel: Mapped[DeliveryChannel] = mapped_column(
        Enum(DeliveryChannel, name="delivery_channel"), nullable=False, default=DeliveryChannel.in_app
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status"), nullable=False, default=NotificationStatus.pending
    )

    __table_args__ = (
        Index("idx_notifications_user_deleted", "user_id", "deleted_at"),
        Index(
            "idx_notifications_user_read_active",
            "user_id",
            "read_at",
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        Index("idx_notifications_pending_schedule", "status", "scheduled_at"),
    )
