from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.api.v1._responses import error_response, success_response
from app.db.repositories.user_repository import UserRepository
from app.db.session import SessionLocal
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired token"},
        ) from exc

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Access token required"},
        )

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token subject missing"},
        )
    return str(subject)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(UserRepository(db))
    try:
        result = auth_service.register(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )
        return success_response(result, status_code=status.HTTP_201_CREATED)
    except ValueError as exc:
        if str(exc) == "EMAIL_ALREADY_EXISTS":
            return error_response("VALIDATION_ERROR", "Email already exists", status.HTTP_409_CONFLICT)
        return error_response("INTERNAL_ERROR", "Internal server error", status.HTTP_500_INTERNAL_SERVER_ERROR)
    except IntegrityError as exc:
        detail = str(getattr(exc, "orig", exc)).lower()
        if "uq_users_email" in detail or "users_email_key" in detail or "unique constraint" in detail:
            return error_response(
                "VALIDATION_ERROR",
                "Email already exists",
                status.HTTP_409_CONFLICT,
                fields={"email": "Email already exists"},
            )
        if "null value" in detail and "id" in detail:
            return error_response(
                "DATABASE_MIGRATION_REQUIRED",
                "Database schema does not match this API (e.g. users.id has no default). Run Alembic migrations to head, e.g. scripts/migrate.ps1 or: docker compose exec app alembic upgrade head.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return error_response("INTERNAL_ERROR", "Registration failed", status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(UserRepository(db))
    try:
        result = auth_service.login(email=payload.email, password=payload.password)
        return success_response(result)
    except ValueError as exc:
        if str(exc) == "INVALID_CREDENTIALS":
            return error_response("PERMISSION_DENIED", "Invalid email or password", status.HTTP_401_UNAUTHORIZED)
        return error_response("INTERNAL_ERROR", "Internal server error", status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(UserRepository(db))
    try:
        result = auth_service.refresh(payload.refresh_token)
        return success_response(result)
    except ValueError as exc:
        if str(exc) == "INVALID_TOKEN":
            return error_response("INVALID_TOKEN", "Invalid or expired refresh token", status.HTTP_401_UNAUTHORIZED)
        if str(exc) == "PERMISSION_DENIED":
            return error_response("PERMISSION_DENIED", "User not found", status.HTTP_403_FORBIDDEN)
        return error_response("INTERNAL_ERROR", "Internal server error", status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/me")
def me(db: Session = Depends(get_db), current_user_id: str = Depends(get_current_user_id)):
    auth_service = AuthService(UserRepository(db))
    try:
        result = auth_service.get_me(current_user_id)
        return success_response(result)
    except ValueError as exc:
        if str(exc) == "PERMISSION_DENIED":
            return error_response("PERMISSION_DENIED", "User not found", status.HTTP_403_FORBIDDEN)
        return error_response("INTERNAL_ERROR", "Internal server error", status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/protected-test")
def protected_test(current_user_id: str = Depends(get_current_user_id)):
    try:
        int(current_user_id)
    except ValueError:
        return error_response("INVALID_TOKEN", "Invalid user id in token", status.HTTP_401_UNAUTHORIZED)
    return success_response(
        {
            "message": "JWT access token is valid",
            "user_id": current_user_id,
        }
    )
