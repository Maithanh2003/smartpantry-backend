from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import PantryCategories

CATEGORY_SEED_DATA = [
    {"code": "vegetable", "name": "Vegetable"},
    {"code": "fruit", "name": "Fruit"},
    {"code": "meat", "name": "Meat"},
    {"code": "seafood", "name": "Seafood"},
    {"code": "dairy", "name": "Dairy"},
    {"code": "grain", "name": "Grain"},
    {"code": "beverage", "name": "Beverage"},
    {"code": "other", "name": "Other"},
]


def seed_pantry_categories(db: Session) -> None:
    stmt = insert(PantryCategories).values(CATEGORY_SEED_DATA)
    stmt = stmt.on_conflict_do_nothing(index_elements=["code"])
    db.execute(stmt)
    db.commit()
