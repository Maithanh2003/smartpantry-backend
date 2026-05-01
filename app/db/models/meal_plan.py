import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import MealPlanStatus
from app.db.models.mixins import SoftDeleteMixin, TimestampMixin


class MealPlans(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "meal_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    plan_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[MealPlanStatus] = mapped_column(
        Enum(MealPlanStatus, name="meal_plan_status"), nullable=False, default=MealPlanStatus.draft
    )
    content_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (Index("idx_meal_plans_user_status_date", "user_id", "status", "plan_date"),)
