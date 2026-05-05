from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1._responses import error_response, success_response
from app.api.v1.auth import get_current_user_id, get_db
from app.core.redis_client import get_redis_client
from app.db.repositories.pantry_category_repository import PantryCategoryRepository
from app.db.repositories.pantry_repository import PantryRepository
from app.schemas.pantry import PantryCreateRequest, PantryUpdateRequest
from app.services.pantry_cache_service import PantryCacheService
from app.services.pantry_service import PantryService
from settings import get_settings

router = APIRouter(prefix="/pantry-items", tags=["pantry"])
settings = get_settings()


def get_pantry_cache_service() -> PantryCacheService:
    return PantryCacheService(
        get_redis_client(),
        enabled=settings.pantry_list_cache_enabled,
        ttl_seconds=settings.pantry_list_cache_ttl_seconds,
        key_prefix=settings.pantry_list_cache_key_prefix,
    )


def _build_pantry_service(db: Session, pantry_cache_service: PantryCacheService) -> PantryService:
    return PantryService(
        PantryRepository(db),
        PantryCategoryRepository(db),
        pantry_cache_service=pantry_cache_service,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_pantry_item(
    payload: PantryCreateRequest,
    db: Session = Depends(get_db),
    pantry_cache_service: PantryCacheService = Depends(get_pantry_cache_service),
    current_user_id: str = Depends(get_current_user_id),
):
    pantry_service = _build_pantry_service(db, pantry_cache_service)
    try:
        result = pantry_service.create_item(current_user_id, payload.model_dump())
        return success_response(result, status_code=status.HTTP_201_CREATED)
    except ValueError as exc:
        return error_response("VALIDATION_ERROR", str(exc), status.HTTP_400_BAD_REQUEST)
    except IntegrityError as exc:
        detail = str(getattr(exc, "orig", exc)).lower()
        if "category_id" in detail or "fk_pantry_items_category_id" in detail:
            m = "category_id must reference an existing pantry category"
            return error_response(
                "VALIDATION_ERROR",
                m,
                status.HTTP_400_BAD_REQUEST,
                fields={"category_id": m},
            )
        return error_response(
            "VALIDATION_ERROR",
            "Pantry item violates database constraints",
            status.HTTP_400_BAD_REQUEST,
        )


@router.get("")
def list_pantry_items(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category_id: int | None = Query(default=None, ge=1),
    expiry_status: str | None = Query(default=None),
    source: str | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=200),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    db: Session = Depends(get_db),
    pantry_cache_service: PantryCacheService = Depends(get_pantry_cache_service),
    current_user_id: str = Depends(get_current_user_id),
):
    pantry_service = _build_pantry_service(db, pantry_cache_service)
    try:
        rows, total = pantry_service.list_items(
            current_user_id,
            page,
            page_size,
            category_id=category_id,
            expiry_status=expiry_status,
            source=source,
            q=q,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return success_response(
            rows,
            meta={
                "page": page,
                "page_size": page_size,
                "total": total,
                "filters": {
                    "category_id": category_id,
                    "expiry_status": expiry_status,
                    "source": source,
                    "q": q,
                },
                "sort": {"by": sort_by, "order": sort_order},
            },
        )
    except ValueError as exc:
        return error_response("VALIDATION_ERROR", str(exc), status.HTTP_400_BAD_REQUEST)


@router.get("/{item_id}")
def get_pantry_item(
    item_id: int,
    db: Session = Depends(get_db),
    pantry_cache_service: PantryCacheService = Depends(get_pantry_cache_service),
    current_user_id: str = Depends(get_current_user_id),
):
    pantry_service = _build_pantry_service(db, pantry_cache_service)
    try:
        return success_response(pantry_service.get_item(current_user_id, item_id))
    except ValueError as exc:
        if str(exc) == "ITEM_NOT_FOUND":
            return error_response("ITEM_NOT_FOUND", "Pantry item not found", status.HTTP_404_NOT_FOUND)
        return error_response("VALIDATION_ERROR", str(exc), status.HTTP_400_BAD_REQUEST)


@router.patch("/{item_id}")
def update_pantry_item(
    item_id: str,
    payload: PantryUpdateRequest,
    db: Session = Depends(get_db),
    pantry_cache_service: PantryCacheService = Depends(get_pantry_cache_service),
    current_user_id: str = Depends(get_current_user_id),
):
    pantry_service = _build_pantry_service(db, pantry_cache_service)
    try:
        result = pantry_service.update_item(
            current_user_id,
            item_id,
            payload.model_dump(exclude_none=True),
        )
        return success_response(result)
    except ValueError as exc:
        if str(exc) == "ITEM_NOT_FOUND":
            return error_response("ITEM_NOT_FOUND", "Pantry item not found", status.HTTP_404_NOT_FOUND)
        return error_response("VALIDATION_ERROR", str(exc), status.HTTP_400_BAD_REQUEST)
    except IntegrityError as exc:
        detail = str(getattr(exc, "orig", exc)).lower()
        if "category_id" in detail or "fk_pantry_items_category_id" in detail:
            m = "category_id must reference an existing pantry category"
            return error_response(
                "VALIDATION_ERROR",
                m,
                status.HTTP_400_BAD_REQUEST,
                fields={"category_id": m},
            )
        return error_response(
            "VALIDATION_ERROR",
            "Pantry item violates database constraints",
            status.HTTP_400_BAD_REQUEST,
        )


@router.delete("/{item_id}")
def delete_pantry_item(
    item_id: str,
    db: Session = Depends(get_db),
    pantry_cache_service: PantryCacheService = Depends(get_pantry_cache_service),
    current_user_id: str = Depends(get_current_user_id),
):
    pantry_service = _build_pantry_service(db, pantry_cache_service)
    try:
        pantry_service.delete_item(current_user_id, item_id)
        return success_response({"deleted": True, "item_id": item_id})
    except ValueError:
        return error_response("ITEM_NOT_FOUND", "Pantry item not found", status.HTTP_404_NOT_FOUND)
