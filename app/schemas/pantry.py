from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class PantryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category_id: int | None = None
    quantity_value: Decimal = Field(gt=0)
    quantity_unit: str = Field(min_length=1, max_length=32)
    source: str = Field(default="manual")
    notes: str | None = None
    expiry_date: date | None = None
    image_path: str | None = None

    @field_validator("image_path", mode="before")
    @classmethod
    def normalize_image_path(cls, v: object) -> str | None:
        if v is None or v == "":
            return None
        if not isinstance(v, str):
            raise ValueError("image_path must be a string or null")
        s = v.strip()
        if not s:
            return None
        if "://" in s or s.startswith(("/", "\\")):
            raise ValueError("image_path must be relative object path")
        return s


class PantryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category_id: int | None = None
    quantity_value: Decimal | None = Field(default=None, gt=0)
    quantity_unit: str | None = Field(default=None, min_length=1, max_length=32)
    source: str | None = None
    notes: str | None = None
    expiry_date: date | None = None
    image_path: str | None = None

    @field_validator("image_path", mode="before")
    @classmethod
    def normalize_image_path_update(cls, v: object) -> str | None:
        if v is None:
            return None
        if v == "":
            return None
        if not isinstance(v, str):
            raise ValueError("image_path must be a string or null")
        s = v.strip()
        if not s:
            return None
        if "://" in s or s.startswith(("/", "\\")):
            raise ValueError("image_path must be relative object path")
        return s


class PantryItemResponse(BaseModel):
    id: int
    user_id: int
    category_id: int | None
    name: str
    quantity_value: Decimal
    quantity_unit: str
    source: str
    notes: str | None
    expiry_date: date | None
    expiry_status: str
    image_path: str | None
    image_url: str | None = None
    created_at: datetime
    updated_at: datetime
