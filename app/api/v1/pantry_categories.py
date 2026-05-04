from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1._responses import error_response, success_response
from app.api.v1.auth import get_current_user_id, get_db
from app.db.repositories.pantry_category_repository import PantryCategoryRepository
from app.schemas.pantry_category import PantryCategoryCreateRequest, PantryCategoryUpdateRequest
from app.services.pantry_category_service import PantryCategoryService

router = APIRouter(prefix="/pantry-categories", tags=["pantry-categories"])


@router.get("")
def list_pantry_categories(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    service = PantryCategoryService(PantryCategoryRepository(db))
    rows, total = service.list_categories(page, page_size)
    return success_response(rows, meta={"page": page, "page_size": page_size, "total": total})


@router.get("/{category_id}")
def get_pantry_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    service = PantryCategoryService(PantryCategoryRepository(db))
    try:
        return success_response(service.get_category(category_id))
    except ValueError:
        return error_response("ITEM_NOT_FOUND", "Pantry category not found", status.HTTP_404_NOT_FOUND)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_pantry_category(
    payload: PantryCategoryCreateRequest,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    service = PantryCategoryService(PantryCategoryRepository(db))
    try:
        return success_response(service.create_category(payload.model_dump()), status_code=status.HTTP_201_CREATED)
    except ValueError:
        return error_response("VALIDATION_ERROR", "Category code already exists", status.HTTP_409_CONFLICT)


@router.patch("/{category_id}")
def update_pantry_category(
    category_id: int,
    payload: PantryCategoryUpdateRequest,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    service = PantryCategoryService(PantryCategoryRepository(db))
    try:
        return success_response(service.update_category(category_id, payload.model_dump(exclude_none=True)))
    except ValueError as exc:
        if str(exc) == "CATEGORY_NOT_FOUND":
            return error_response("ITEM_NOT_FOUND", "Pantry category not found", status.HTTP_404_NOT_FOUND)
        return error_response("VALIDATION_ERROR", "Category code already exists", status.HTTP_409_CONFLICT)


@router.delete("/{category_id}")
def delete_pantry_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    service = PantryCategoryService(PantryCategoryRepository(db))
    try:
        service.delete_category(category_id)
        return success_response({"deleted": True, "category_id": category_id})
    except ValueError:
        return error_response("ITEM_NOT_FOUND", "Pantry category not found", status.HTTP_404_NOT_FOUND)
