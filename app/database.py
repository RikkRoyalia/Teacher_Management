import os

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./teacher_management.db")


class Base(DeclarativeBase):
    pass


def create_database(database_url: str = DATABASE_URL) -> tuple[Engine, sessionmaker]:
    if database_url.startswith("sqlite"):
        if database_url in {"sqlite://", "sqlite:///:memory:"}:
            engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            engine = create_engine(
                database_url, connect_args={"check_same_thread": False}
            )
    else:
        engine = create_engine(database_url)

    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(dbapi_connection: object, connection_record: object) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
