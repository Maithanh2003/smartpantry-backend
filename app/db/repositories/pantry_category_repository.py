from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import PantryCategories


class PantryCategoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, limit: int = 20, offset: int = 0) -> list[PantryCategories]:
        stmt = (
            select(PantryCategories)
            .order_by(PantryCategories.id.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count(self) -> int:
        stmt = select(func.count(PantryCategories.id))
        return int(self.db.execute(stmt).scalar_one())

    def get_by_id(self, category_id: int) -> PantryCategories | None:
        stmt = select(PantryCategories).where(PantryCategories.id == category_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_code(self, code: str) -> PantryCategories | None:
        stmt = select(PantryCategories).where(PantryCategories.code == code.lower())
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, code: str, name: str) -> PantryCategories:
        category = PantryCategories(code=code.lower(), name=name)
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def update(self, category: PantryCategories, payload: dict) -> PantryCategories:
        for key, value in payload.items():
            if key == "code" and isinstance(value, str):
                value = value.lower()
            setattr(category, key, value)
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def delete(self, category: PantryCategories) -> None:
        self.db.delete(category)
        self.db.commit()
