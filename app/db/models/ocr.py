import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import OcrParseStatus
from app.db.models.mixins import TimestampMixin


class OcrReceipts(Base, TimestampMixin):
    __tablename__ = "ocr_receipts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_status: Mapped[OcrParseStatus] = mapped_column(
        Enum(OcrParseStatus, name="ocr_parse_status"), nullable=False, default=OcrParseStatus.uploaded
    )
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OcrCandidates(Base, TimestampMixin):
    __tablename__ = "ocr_candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    receipt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ocr_receipts.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name_raw: Mapped[str] = mapped_column(String(255), nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    quantity_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    is_confirmed: Mapped[bool] = mapped_column(nullable=False, default=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "receipt_id",
            "name_normalized",
            "quantity_value",
            "quantity_unit",
            name="uq_ocr_candidates_dedup",
        ),
        CheckConstraint("quantity_value > 0", name="ocr_quantity_value_positive"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ocr_confidence_range"),
    )
