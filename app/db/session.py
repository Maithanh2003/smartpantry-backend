from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from settings import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@event.listens_for(engine, "connect")
def set_db_timezone(dbapi_connection, connection_record) -> None:  # noqa: ANN001,ARG001
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SET TIME ZONE %s", (settings.db_timezone,))
