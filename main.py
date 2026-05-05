from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from redis.exceptions import RedisError
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from starlette.requests import Request

from app.api.v1._responses import error_response, format_validation_error_fields
from app.api.v1.auth import router as auth_router
from app.api.v1.pantry import router as pantry_router
from app.api.v1.pantry_categories import router as pantry_categories_router
from app.core.redis_client import get_redis_client
from settings import get_settings

app = FastAPI(title="SmartPantry API")
settings = get_settings()


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    primary, fields = format_validation_error_fields(exc.errors())
    return error_response("VALIDATION_ERROR", primary, 400, fields=fields)
engine = create_engine(settings.database_url, pool_pre_ping=True)
redis_client = get_redis_client()

allowed_origins = settings.cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(pantry_router, prefix="/api/v1")
app.include_router(pantry_categories_router, prefix="/api/v1")

@app.get("/health")
def health():
    db_status = "ok"
    redis_status = "ok"
    status = "ok"

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError:
        db_status = "error"
        status = "degraded"

    try:
        redis_client.ping()
    except RedisError:
        redis_status = "error"
        status = "degraded"

    return {"status": status, "db": db_status, "redis": redis_status}