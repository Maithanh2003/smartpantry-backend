from app.db.repositories.pantry_category_repository import PantryCategoryRepository


class PantryCategoryService:
    def __init__(self, category_repo: PantryCategoryRepository) -> None:
        self.category_repo = category_repo

    def list_categories(self, page: int, page_size: int) -> tuple[list[dict], int]:
        limit = page_size
        offset = (page - 1) * page_size
        rows = self.category_repo.list(limit=limit, offset=offset)
        total = self.category_repo.count()
        return [self._serialize(row) for row in rows], total

    def get_category(self, category_id: int) -> dict:
        row = self.category_repo.get_by_id(category_id)
        if not row:
            raise ValueError("CATEGORY_NOT_FOUND")
        return self._serialize(row)

    def create_category(self, payload: dict) -> dict:
        if self.category_repo.get_by_code(payload["code"]):
            raise ValueError("VALIDATION_ERROR")
        row = self.category_repo.create(code=payload["code"], name=payload["name"])
        return self._serialize(row)

    def update_category(self, category_id: int, payload: dict) -> dict:
        row = self.category_repo.get_by_id(category_id)
        if not row:
            raise ValueError("CATEGORY_NOT_FOUND")

        new_code = payload.get("code")
        if new_code:
            existing = self.category_repo.get_by_code(new_code)
            if existing and existing.id != category_id:
                raise ValueError("VALIDATION_ERROR")

        row = self.category_repo.update(row, payload)
        return self._serialize(row)

    def delete_category(self, category_id: int) -> None:
        row = self.category_repo.get_by_id(category_id)
        if not row:
            raise ValueError("CATEGORY_NOT_FOUND")
        self.category_repo.delete(row)

    @staticmethod
    def _serialize(row) -> dict:
        return {
            "id": row.id,
            "code": row.code,
            "name": row.name,
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
        }
