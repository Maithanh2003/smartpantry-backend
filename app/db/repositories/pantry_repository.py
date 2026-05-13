from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select, true as sql_true
from sqlalchemy.orm import Session

from app.db.models import PantryItems
from app.db.models.enums import ExpiryStatus, PantryItemSource


class PantryRepository:
    """Ownership-safe repository for pantry item queries (soft-delete aware)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _ownership_active(user_id: int):
        return and_(PantryItems.user_id == user_id, PantryItems.deleted_at.is_(None))

    @staticmethod
    def _ownership_any(user_id: int):
        return PantryItems.user_id == user_id

    @staticmethod
    def _list_filters(
        *,
        category_id: int | None,
        expiry_status: ExpiryStatus | None,
        source: PantryItemSource | None,
        q: str | None,
    ):
        parts: list = []
        if category_id is not None:
            parts.append(PantryItems.category_id == category_id)
        if expiry_status is not None:
            parts.append(PantryItems.expiry_status == expiry_status)
        if source is not None:
            parts.append(PantryItems.source == source)
        if q:
            keyword = f"%{q.strip()}%"
            parts.append(
                or_(
                    PantryItems.name.ilike(keyword),
                    PantryItems.notes.ilike(keyword),
                )
            )
        return and_(*parts) if parts else sql_true()

    @staticmethod
    def _order_column(sort_by: str):
        sort_columns = {
            "created_at": PantryItems.created_at,
            "updated_at": PantryItems.updated_at,
            "expiry_date": PantryItems.expiry_date,
            "name": PantryItems.name,
        }
        return sort_columns.get(sort_by, PantryItems.created_at)

    def get_by_id_and_user(self, item_id: int, user_id: int) -> PantryItems | None:
        stmt = select(PantryItems).where(
            PantryItems.id == item_id,
            self._ownership_active(user_id),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_id_for_user_including_deleted(self, item_id: int, user_id: int) -> PantryItems | None:
        stmt = select(PantryItems).where(
            PantryItems.id == item_id,
            self._ownership_any(user_id),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_user(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
        *,
        category_id: int | None = None,
        expiry_status: ExpiryStatus | None = None,
        source: PantryItemSource | None = None,
        q: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[PantryItems]:
        filters = self._list_filters(
            category_id=category_id,
            expiry_status=expiry_status,
            source=source,
            q=q,
        )
        stmt = (
            select(PantryItems)
            .where(self._ownership_active(user_id))
            .where(filters)
        )
        order_column = self._order_column(sort_by)
        order_clause = order_column.asc() if sort_order == "asc" else order_column.desc()
        stmt = stmt.order_by(order_clause).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def count_by_user(
        self,
        user_id: int,
        *,
        category_id: int | None = None,
        expiry_status: ExpiryStatus | None = None,
        source: PantryItemSource | None = None,
        q: str | None = None,
    ) -> int:
        filters = self._list_filters(
            category_id=category_id,
            expiry_status=expiry_status,
            source=source,
            q=q,
        )
        stmt = (
            select(func.count(PantryItems.id))
            .select_from(PantryItems)
            .where(self._ownership_active(user_id))
            .where(filters)
        )
        return int(self.db.execute(stmt).scalar_one())

    def create(self, user_id: int, payload: dict[str, Any]) -> PantryItems:
        item = PantryItems(user_id=user_id, **payload)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update(self, item: PantryItems, payload: dict[str, Any]) -> PantryItems:
        payload = {k: v for k, v in payload.items() if k != "deleted_at"}
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

    def restore(self, item: PantryItems) -> PantryItems:
        if item.deleted_at is None:
            raise ValueError("ITEM_NOT_DELETED")
        item.deleted_at = None
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item
