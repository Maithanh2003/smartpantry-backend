from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import PantryItems


class PantryRepository:
    """Ownership-safe repository for pantry item queries."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id_and_user(self, item_id: int, user_id: int) -> PantryItems | None:
        stmt = select(PantryItems).where(
            PantryItems.id == item_id,
            PantryItems.user_id == user_id,
            PantryItems.deleted_at.is_(None),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_user(self, user_id: int, limit: int = 20, offset: int = 0) -> list[PantryItems]:
        stmt = (
            select(PantryItems)
            .where(PantryItems.user_id == user_id, PantryItems.deleted_at.is_(None))
            .order_by(PantryItems.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_by_user(self, user_id: int) -> int:
        stmt = select(func.count(PantryItems.id)).where(
            PantryItems.user_id == user_id,
            PantryItems.deleted_at.is_(None),
        )
        return int(self.db.execute(stmt).scalar_one())

    def create(self, user_id: int, payload: dict[str, Any]) -> PantryItems:
        item = PantryItems(user_id=user_id, **payload)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update(self, item: PantryItems, payload: dict[str, Any]) -> PantryItems:
        for key, value in payload.items():
            setattr(item, key, value)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def soft_delete(self, item: PantryItems) -> None:
        item.deleted_at = datetime.now(UTC)
        self.db.add(item)
        self.db.commit()
