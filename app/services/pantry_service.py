from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.core.media_urls import public_object_url
from app.db.models.enums import ExpiryStatus, PantryItemSource
from app.db.repositories.pantry_category_repository import PantryCategoryRepository
from app.db.repositories.pantry_repository import PantryRepository
from app.services.pantry_cache_service import PantryCacheService

MAX_PANTRY_LIST_PAGE = 10_000


def _compute_expiry_status(expiry_date: date | None) -> ExpiryStatus:
    """Derive expiry_status from expiry_date (UTC calendar day).

    Rules (single source of truth for API + persisted column on write):
    - No expiry_date -> fresh (no expiry signal).
    - expiry_date < today -> expired.
    - 0 <= days until expiry <= 3 -> warning (includes today through 3 days ahead).
    - Otherwise -> fresh.
    """
    if expiry_date is None:
        return ExpiryStatus.fresh
    today = datetime.now(UTC).date()
    delta = (expiry_date - today).days
    if delta < 0:
        return ExpiryStatus.expired
    if delta <= 3:
        return ExpiryStatus.warning
    return ExpiryStatus.fresh


class PantryService:
    def __init__(
        self,
        pantry_repo: PantryRepository,
        category_repo: PantryCategoryRepository | None = None,
        pantry_cache_service: PantryCacheService | None = None,
        *,
        image_public_base_url: str | None = None,
    ) -> None:
        self.pantry_repo = pantry_repo
        self.category_repo = category_repo
        self.pantry_cache_service = pantry_cache_service
        self._image_public_base_url = image_public_base_url

    def _invalidate_user_list_cache(self, user_id: int) -> None:
        if self.pantry_cache_service is None:
            return
        self.pantry_cache_service.invalidate_user_pantry_list(user_id)

    def _ensure_category(self, category_id: int | None) -> None:
        if category_id is None:
            return
        if self.category_repo is None:
            raise ValueError("category_id cannot be validated (internal configuration error)")
        if not self.category_repo.get_by_id(int(category_id)):
            raise ValueError("category_id must reference an existing pantry category")

    def create_item(self, user_id: str, payload: dict) -> dict:
        self._ensure_category(payload.get("category_id"))

        # Server-owned: never trust client-sent expiry_status
        payload.pop("expiry_status", None)
        payload.pop("deleted_at", None)
        expiry_date = payload.get("expiry_date")
        payload["expiry_status"] = _compute_expiry_status(expiry_date)
        raw_source = payload.get("source", PantryItemSource.manual.value)
        try:
            payload["source"] = PantryItemSource(raw_source)
        except ValueError as exc:
            allowed = ", ".join(sorted(e.value for e in PantryItemSource))
            raise ValueError(f"source must be one of: {allowed}") from exc

        item = self.pantry_repo.create(int(user_id), payload)
        self._invalidate_user_list_cache(int(user_id))
        return self._serialize(item)

    def list_items(
        self,
        user_id: str,
        page: int,
        page_size: int,
        *,
        category_id: int | None = None,
        expiry_status: str | None = None,
        source: str | None = None,
        q: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[dict], int]:
        if page < 1 or page > MAX_PANTRY_LIST_PAGE:
            raise ValueError(f"page must be between 1 and {MAX_PANTRY_LIST_PAGE}")
        if page_size < 1 or page_size > 100:
            raise ValueError("page_size must be between 1 and 100")

        limit = page_size
        offset = (page - 1) * page_size
        parsed_expiry_status = None
        if expiry_status is not None:
            try:
                parsed_expiry_status = ExpiryStatus(expiry_status)
            except ValueError as exc:
                allowed = ", ".join(sorted(e.value for e in ExpiryStatus))
                raise ValueError(f"expiry_status must be one of: {allowed}") from exc

        parsed_source = None
        if source is not None:
            try:
                parsed_source = PantryItemSource(source)
            except ValueError as exc:
                allowed = ", ".join(sorted(e.value for e in PantryItemSource))
                raise ValueError(f"source must be one of: {allowed}") from exc

        allowed_sort_fields = {"created_at", "updated_at", "expiry_date", "name"}
        if sort_by not in allowed_sort_fields:
            raise ValueError("sort_by must be one of: created_at, updated_at, expiry_date, name")
        if sort_order not in {"asc", "desc"}:
            raise ValueError("sort_order must be one of: asc, desc")

        query_state: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
            "category_id": category_id,
            "expiry_status": parsed_expiry_status.value if parsed_expiry_status else None,
            "source": parsed_source.value if parsed_source else None,
            "q": q,
            "sort_by": sort_by,
            "sort_order": sort_order,
        }

        if self.pantry_cache_service is not None:
            cached = self.pantry_cache_service.get_pantry_list(user_id=int(user_id), query_state=query_state)
            if cached is not None:
                return cached

        rows = self.pantry_repo.list_by_user(
            int(user_id),
            limit=limit,
            offset=offset,
            category_id=category_id,
            expiry_status=parsed_expiry_status,
            source=parsed_source,
            q=q,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        total = self.pantry_repo.count_by_user(
            int(user_id),
            category_id=category_id,
            expiry_status=parsed_expiry_status,
            source=parsed_source,
            q=q,
        )
        serialized = [self._serialize(row) for row in rows]

        if self.pantry_cache_service is not None:
            self.pantry_cache_service.set_pantry_list(
                user_id=int(user_id),
                query_state=query_state,
                rows=serialized,
                total=total,
            )
        return serialized, total

    def get_item(self, user_id: str, item_id: int) -> dict:
        item = self.pantry_repo.get_by_id_and_user(item_id, int(user_id))
        if not item:
            raise ValueError("ITEM_NOT_FOUND")
        return self._serialize(item)

    def update_item(self, user_id: str, item_id: str, payload: dict) -> tuple[dict, dict]:
        item = self.pantry_repo.get_by_id_and_user(int(item_id), int(user_id))
        if not item:
            raise ValueError("ITEM_NOT_FOUND")

        before = self._serialize(item)

        if "category_id" in payload:
            self._ensure_category(payload.get("category_id"))

        # Server-owned: recompute from effective expiry after patch
        payload.pop("expiry_status", None)
        payload.pop("deleted_at", None)
        effective_expiry = payload["expiry_date"] if "expiry_date" in payload else item.expiry_date
        payload["expiry_status"] = _compute_expiry_status(effective_expiry)

        if "source" in payload and payload["source"] is not None:
            try:
                payload["source"] = PantryItemSource(payload["source"])
            except ValueError as exc:
                allowed = ", ".join(sorted(e.value for e in PantryItemSource))
                raise ValueError(f"source must be one of: {allowed}") from exc

        item = self.pantry_repo.update(item, payload)
        self._invalidate_user_list_cache(int(user_id))
        return self._serialize(item), before

    def delete_item(self, user_id: str, item_id: str) -> dict:
        item = self.pantry_repo.get_by_id_and_user(int(item_id), int(user_id))
        if not item:
            raise ValueError("ITEM_NOT_FOUND")
        snapshot = self._serialize(item)
        self.pantry_repo.soft_delete(item)
        self._invalidate_user_list_cache(int(user_id))
        return snapshot

    def restore_item(self, user_id: str, item_id: int) -> dict:
        item = self.pantry_repo.get_by_id_for_user_including_deleted(item_id, int(user_id))
        if not item:
            raise ValueError("ITEM_NOT_FOUND")
        restored = self.pantry_repo.restore(item)
        self._invalidate_user_list_cache(int(user_id))
        return self._serialize(restored)

    def _serialize(self, item) -> dict:
        path = item.image_path
        return {
            "id": item.id,
            "user_id": item.user_id,
            "category_id": item.category_id,
            "name": item.name,
            "quantity_value": str(Decimal(item.quantity_value)),
            "quantity_unit": item.quantity_unit,
            "source": item.source.value,
            "notes": item.notes,
            "expiry_date": item.expiry_date.isoformat() if item.expiry_date else None,
            "expiry_status": _compute_expiry_status(item.expiry_date).value,
            "image_path": path,
            "image_url": public_object_url(self._image_public_base_url, path),
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }
