import uuid

from sqlalchemy import Enum, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import UserStatus
from app.db.models.mixins import SoftDeleteMixin, TimestampMixin


class Users(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    avatar_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"), nullable=False, default=UserStatus.active
    )

    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)
