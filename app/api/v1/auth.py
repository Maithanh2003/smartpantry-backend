from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.repositories.user_repository import UserRepository
from app.db.session import SessionLocal
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _success_response(data: dict) -> dict:
    return {
        "success": True,
        "data": data,
        "meta": {
            "request_id": str(uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }


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
        return _success_response(result)
    except ValueError as exc:
        if str(exc) == "EMAIL_ALREADY_EXISTS":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "VALIDATION_ERROR", "message": "Email already exists"},
            ) from exc
        raise


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(UserRepository(db))
    try:
        result = auth_service.login(email=payload.email, password=payload.password)
        return _success_response(result)
    except ValueError as exc:
        if str(exc) == "INVALID_CREDENTIALS":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "PERMISSION_DENIED", "message": "Invalid email or password"},
            ) from exc
        raise


@router.get("/protected-test")
def protected_test(current_user_id: str = Depends(get_current_user_id)):
    return _success_response(
        {
            "message": "JWT access token is valid",
            "user_id": current_user_id,
        }
    )
