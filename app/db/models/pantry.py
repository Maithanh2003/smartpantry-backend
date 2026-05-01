import uuid
from datetime import date

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import ExpiryStatus, PantryItemSource
from app.db.models.mixins import SoftDeleteMixin, TimestampMixin


class PantryCategories(Base, TimestampMixin):
    __tablename__ = "pantry_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    __table_args__ = (UniqueConstraint("code", name="uq_pantry_categories_code"),)


class PantryItems(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "pantry_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("pantry_categories.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    quantity_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[PantryItemSource] = mapped_column(
        Enum(PantryItemSource, name="pantry_item_source"), nullable=False, default=PantryItemSource.manual
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_status: Mapped[ExpiryStatus] = mapped_column(
        Enum(ExpiryStatus, name="expiry_status"), nullable=False, default=ExpiryStatus.fresh
    )
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        CheckConstraint("quantity_value > 0", name="quantity_value_positive"),
        Index("idx_pantry_items_user_deleted", "user_id", "deleted_at"),
        Index(
            "idx_pantry_items_user_expiry_date_active",
            "user_id",
            "expiry_date",
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        Index(
            "idx_pantry_items_user_expiry_status_active",
            "user_id",
            "expiry_status",
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
    )
