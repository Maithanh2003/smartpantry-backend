import logging
import os
from contextlib import asynccontextmanager

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


def configure_app_logging() -> None:
    """Emit INFO from ``app.*`` (e.g. pantry Redis cache) without being dropped by root WARNING.

    Child loggers propagate to ``app``; if we only set ``app`` level to INFO but leave
    ``propagate=True``, the record then hits ``root`` where ``getEffectiveLevel()`` is often
    WARNING, so ``Logger.handle`` discards INFO before any handler runs. We attach a handler
    on ``app`` and stop propagation at that subtree.
    """
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    app_log = logging.getLogger("app")
    app_log.setLevel(level)
    app_log.propagate = False
    if not app_log.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
        app_log.addHandler(handler)


configure_app_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_app_logging()
    yield


app = FastAPI(title="SmartPantry API", lifespan=lifespan)


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
