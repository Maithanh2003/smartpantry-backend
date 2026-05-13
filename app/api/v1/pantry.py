from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.api.v1._responses import error_response, success_response
from app.api.v1.auth import get_current_user_id, get_db
from app.core.object_storage import ObjectStorageClient, ObjectStorageConfig
from app.core.redis_client import get_redis_client
from app.core.request_context import client_ip, client_user_agent
from app.db.repositories.audit_repository import AuditRepository
from app.db.repositories.pantry_category_repository import PantryCategoryRepository
from app.db.repositories.pantry_repository import PantryRepository
from app.schemas.pantry import PantryCreateRequest, PantryUpdateRequest
from app.services.pantry_cache_service import PantryCacheService
from app.services.pantry_service import MAX_PANTRY_LIST_PAGE, PantryService
from app.services.pantry_upload_service import PantryUploadService
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
        image_public_base_url=settings.object_storage_public_base_url,
    )


def _audit_write(
    db: Session,
    request: Request,
    *,
    actor_user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: str,
    before_json: dict | None = None,
    after_json: dict | None = None,
) -> None:
    AuditRepository(db).write(
        action=action,
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        before_json=before_json,
        after_json=after_json,
        ip_address=client_ip(request),
        user_agent=client_user_agent(request),
    )


def get_pantry_upload_service() -> PantryUploadService:
    storage_client = ObjectStorageClient(
        ObjectStorageConfig(
            endpoint_url=settings.object_storage_endpoint_url,
            region=settings.object_storage_region,
            bucket=settings.object_storage_bucket,
            access_key_id=settings.object_storage_access_key_id,
            secret_access_key=settings.object_storage_secret_access_key,
        )
    )
    return PantryUploadService(
        storage_client,
        max_size_bytes=settings.pantry_image_max_size_bytes,
        allowed_mime_types=settings.pantry_image_allowed_mime_types,
        image_public_base_url=settings.object_storage_public_base_url,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_pantry_item(
    payload: PantryCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    pantry_cache_service: PantryCacheService = Depends(get_pantry_cache_service),
    current_user_id: str = Depends(get_current_user_id),
):
    pantry_service = _build_pantry_service(db, pantry_cache_service)
    try:
        result = pantry_service.create_item(current_user_id, payload.model_dump())
        _audit_write(
            db,
            request,
            actor_user_id=int(current_user_id),
            action="CREATE",
            entity_type="pantry_item",
            entity_id=str(result["id"]),
            after_json=result,
        )
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


@router.post("/upload-image", status_code=status.HTTP_201_CREATED)
async def upload_pantry_image(
    file: UploadFile = File(...),
    upload_service: PantryUploadService = Depends(get_pantry_upload_service),
    current_user_id: str = Depends(get_current_user_id),
):
    try:
        content = await file.read()
        result = upload_service.upload_pantry_image(
            user_id=int(current_user_id),
            filename=file.filename,
            mime_type=file.content_type,
            content=content,
        )
        return success_response(result, status_code=status.HTTP_201_CREATED)
    except ValueError as exc:
        return error_response("VALIDATION_ERROR", str(exc), status.HTTP_400_BAD_REQUEST)
    except (BotoCoreError, ClientError) as exc:
        msg = str(exc)
        detail = f"Object storage upload failed: {msg}"
        if "amazonaws.com" in msg or "s3.auto.amazonaws.com" in msg:
            detail += (
                " If you use MinIO or Cloudflare R2, set OBJECT_STORAGE_ENDPOINT_URL "
                "(Docker: http://minio:9000; host uvicorn: http://127.0.0.1:9000; R2: "
                "https://<ACCOUNT_ID>.r2.cloudflarestorage.com). "
                "When it is unset, boto3 uses AWS S3 and your bucket name becomes part of the hostname."
            )
        return error_response("INTERNAL_ERROR", detail, status.HTTP_503_SERVICE_UNAVAILABLE)


@router.get("")
def list_pantry_items(
    page: int = Query(default=1, ge=1, le=MAX_PANTRY_LIST_PAGE),
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


@router.post("/{item_id}/restore", status_code=status.HTTP_200_OK)
def restore_pantry_item(
    item_id: int,
    db: Session = Depends(get_db),
    pantry_cache_service: PantryCacheService = Depends(get_pantry_cache_service),
    current_user_id: str = Depends(get_current_user_id),
):
    pantry_service = _build_pantry_service(db, pantry_cache_service)
    try:
        return success_response(pantry_service.restore_item(current_user_id, item_id))
    except ValueError as exc:
        if str(exc) == "ITEM_NOT_FOUND":
            return error_response("ITEM_NOT_FOUND", "Pantry item not found", status.HTTP_404_NOT_FOUND)
        if str(exc) == "ITEM_NOT_DELETED":
            return error_response(
                "ITEM_NOT_DELETED",
                "Pantry item is not deleted",
                status.HTTP_409_CONFLICT,
            )
        return error_response("VALIDATION_ERROR", str(exc), status.HTTP_400_BAD_REQUEST)


@router.patch("/{item_id}")
def update_pantry_item(
    item_id: int,
    payload: PantryUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    pantry_cache_service: PantryCacheService = Depends(get_pantry_cache_service),
    current_user_id: str = Depends(get_current_user_id),
):
    pantry_service = _build_pantry_service(db, pantry_cache_service)
    try:
        result, before = pantry_service.update_item(
            current_user_id,
            str(item_id),
            payload.model_dump(exclude_none=True),
        )
        _audit_write(
            db,
            request,
            actor_user_id=int(current_user_id),
            action="UPDATE",
            entity_type="pantry_item",
            entity_id=str(item_id),
            before_json=before,
            after_json=result,
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
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    pantry_cache_service: PantryCacheService = Depends(get_pantry_cache_service),
    current_user_id: str = Depends(get_current_user_id),
):
    pantry_service = _build_pantry_service(db, pantry_cache_service)
    try:
        snapshot = pantry_service.delete_item(current_user_id, str(item_id))
        _audit_write(
            db,
            request,
            actor_user_id=int(current_user_id),
            action="DELETE",
            entity_type="pantry_item",
            entity_id=str(item_id),
            before_json=snapshot,
        )
        return success_response({"deleted": True, "item_id": item_id})
    except ValueError:
        return error_response("ITEM_NOT_FOUND", "Pantry item not found", status.HTTP_404_NOT_FOUND)
