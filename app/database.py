import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event, inspect, text
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


def migrate_database(database_url: str, engine: Engine) -> None:
    if database_url in {"sqlite://", "sqlite:///:memory:"}:
        Base.metadata.create_all(bind=engine)
        return

    config = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    if engine.dialect.name == "sqlite":
        head_revision = ScriptDirectory.from_config(config).get_current_head()
        database_path = engine.url.database
        if database_path and database_path != ":memory:" and Path(database_path).is_file():
            inspector = inspect(engine)
            version = None
            if "alembic_version" in inspector.get_table_names():
                with engine.connect() as connection:
                    version = connection.scalar(text("SELECT version_num FROM alembic_version"))
            if version != head_revision:
                source_path = Path(database_path).resolve()
                backup_dir = Path(
                    os.getenv(
                        "TEACHER_MANAGEMENT_BACKUP_DIR",
                        str(Path(__file__).parent.parent / ".backups"),
                    )
                )
                backup_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                backup_path = backup_dir / f"pre-migration-{timestamp}.sqlite3"
                with closing(sqlite3.connect(source_path)) as source, closing(
                    sqlite3.connect(backup_path)
                ) as target:
                    source.backup(target)
    command.upgrade(config, "head")
