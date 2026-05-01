import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PantryItems


class PantryRepository:
    """Ownership-safe repository for pantry item queries."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id_and_user(self, item_id: uuid.UUID, user_id: uuid.UUID) -> PantryItems | None:
        stmt = select(PantryItems).where(
            PantryItems.id == item_id,
            PantryItems.user_id == user_id,
            PantryItems.deleted_at.is_(None),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_user(self, user_id: uuid.UUID, limit: int = 20, offset: int = 0) -> list[PantryItems]:
        stmt = (
            select(PantryItems)
            .where(PantryItems.user_id == user_id, PantryItems.deleted_at.is_(None))
            .order_by(PantryItems.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.execute(stmt).scalars().all())
