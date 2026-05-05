from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
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

    def _base_owned_query(self, user_id: int):
        return select(PantryItems).where(
            PantryItems.user_id == user_id,
            PantryItems.deleted_at.is_(None),
        )

    def list_by_user(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
        *,
        category_id: int | None = None,
        expiry_status: str | None = None,
        source: str | None = None,
        q: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[PantryItems]:
        stmt = self._base_owned_query(user_id)
        if category_id is not None:
            stmt = stmt.where(PantryItems.category_id == category_id)
        if expiry_status is not None:
            stmt = stmt.where(PantryItems.expiry_status == expiry_status)
        if source is not None:
            stmt = stmt.where(PantryItems.source == source)
        if q:
            keyword = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    PantryItems.name.ilike(keyword),
                    PantryItems.notes.ilike(keyword),
                )
            )

        sort_columns = {
            "created_at": PantryItems.created_at,
            "updated_at": PantryItems.updated_at,
            "expiry_date": PantryItems.expiry_date,
            "name": PantryItems.name,
        }
        order_column = sort_columns.get(sort_by, PantryItems.created_at)
        order_clause = order_column.asc() if sort_order == "asc" else order_column.desc()

        stmt = stmt.order_by(order_clause).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def count_by_user(
        self,
        user_id: int,
        *,
        category_id: int | None = None,
        expiry_status: str | None = None,
        source: str | None = None,
        q: str | None = None,
    ) -> int:
        stmt = select(func.count(PantryItems.id)).select_from(PantryItems).where(
            PantryItems.user_id == user_id,
            PantryItems.deleted_at.is_(None),
        )
        if category_id is not None:
            stmt = stmt.where(PantryItems.category_id == category_id)
        if expiry_status is not None:
            stmt = stmt.where(PantryItems.expiry_status == expiry_status)
        if source is not None:
            stmt = stmt.where(PantryItems.source == source)
        if q:
            keyword = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    PantryItems.name.ilike(keyword),
                    PantryItems.notes.ilike(keyword),
                )
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
