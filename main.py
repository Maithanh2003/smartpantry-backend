from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from redis import Redis
from redis.exceptions import RedisError

from settings import get_settings

app = FastAPI(title="SmartPantry API")
settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)

allowed_origins = settings.cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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