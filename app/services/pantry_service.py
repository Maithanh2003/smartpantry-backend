from datetime import UTC, date, datetime
from decimal import Decimal

from app.db.models.enums import ExpiryStatus, PantryItemSource
from app.db.repositories.pantry_category_repository import PantryCategoryRepository
from app.db.repositories.pantry_repository import PantryRepository


def _compute_expiry_status(expiry_date: date | None) -> ExpiryStatus:
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
    ) -> None:
        self.pantry_repo = pantry_repo
        self.category_repo = category_repo

    def _ensure_category(self, category_id: int | None) -> None:
        if category_id is None:
            return
        if self.category_repo is None:
            raise ValueError("category_id cannot be validated (internal configuration error)")
        if not self.category_repo.get_by_id(int(category_id)):
            raise ValueError("category_id must reference an existing pantry category")

    def create_item(self, user_id: str, payload: dict) -> dict:
        self._ensure_category(payload.get("category_id"))

        expiry_date = payload.get("expiry_date")
        payload["expiry_status"] = _compute_expiry_status(expiry_date)
        raw_source = payload.get("source", PantryItemSource.manual.value)
        try:
            payload["source"] = PantryItemSource(raw_source)
        except ValueError as exc:
            allowed = ", ".join(sorted(e.value for e in PantryItemSource))
            raise ValueError(f"source must be one of: {allowed}") from exc

        item = self.pantry_repo.create(int(user_id), payload)
        return self._serialize(item)

    def list_items(self, user_id: str, page: int, page_size: int) -> tuple[list[dict], int]:
        limit = page_size
        offset = (page - 1) * page_size
        rows = self.pantry_repo.list_by_user(int(user_id), limit=limit, offset=offset)
        total = self.pantry_repo.count_by_user(int(user_id))
        return [self._serialize(row) for row in rows], total

    def get_item(self, user_id: str, item_id: int) -> dict:
        item = self.pantry_repo.get_by_id_and_user(item_id, int(user_id))
        if not item:
            raise ValueError("ITEM_NOT_FOUND")
        return self._serialize(item)

    def update_item(self, user_id: str, item_id: str, payload: dict) -> dict:
        item = self.pantry_repo.get_by_id_and_user(int(item_id), int(user_id))
        if not item:
            raise ValueError("ITEM_NOT_FOUND")

        if "category_id" in payload:
            self._ensure_category(payload.get("category_id"))

        if "expiry_date" in payload:
            payload["expiry_status"] = _compute_expiry_status(payload.get("expiry_date"))
        if "source" in payload and payload["source"] is not None:
            try:
                payload["source"] = PantryItemSource(payload["source"])
            except ValueError as exc:
                allowed = ", ".join(sorted(e.value for e in PantryItemSource))
                raise ValueError(f"source must be one of: {allowed}") from exc

        item = self.pantry_repo.update(item, payload)
        return self._serialize(item)

    def delete_item(self, user_id: str, item_id: str) -> None:
        item = self.pantry_repo.get_by_id_and_user(int(item_id), int(user_id))
        if not item:
            raise ValueError("ITEM_NOT_FOUND")
        self.pantry_repo.soft_delete(item)

    @staticmethod
    def _serialize(item) -> dict:
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
            "expiry_status": item.expiry_status.value,
            "image_path": item.image_path,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }
