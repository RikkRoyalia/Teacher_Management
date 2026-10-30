import argparse
import os
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from sqlalchemy import make_url

from app.database import DATABASE_URL

PROJECT_ROOT = Path(__file__).parent.parent
UPLOAD_DIR = Path(
    os.getenv("TEACHER_MANAGEMENT_UPLOAD_DIR", str(PROJECT_ROOT / "private_uploads"))
).resolve()
BACKUP_DIR = Path(
    os.getenv("TEACHER_MANAGEMENT_BACKUP_DIR", str(PROJECT_ROOT / ".backups"))
).resolve()


def _database_path() -> Path:
    url = make_url(DATABASE_URL)
    if not url.drivername.startswith("sqlite") or not url.database or url.database == ":memory:":
        raise RuntimeError("Backup and restore require a file-backed SQLite DATABASE_URL.")
    return Path(url.database).resolve()


def create_backup(destination: Path | None = None) -> Path:
    database_path = _database_path()
    if not database_path.is_file():
        raise FileNotFoundError(f"Database file not found: {database_path}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_path = destination or BACKUP_DIR / f"teacher-management-{timestamp}.zip"
    archive_path = archive_path.resolve()
    if archive_path == database_path or archive_path.is_relative_to(UPLOAD_DIR):
        raise ValueError("Backup archive must not overwrite the database or be stored with uploads.")
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=archive_path.parent) as temp_directory:
        snapshot_path = Path(temp_directory) / "teacher_management.db"
        with closing(sqlite3.connect(database_path)) as source, closing(
            sqlite3.connect(snapshot_path)
        ) as snapshot:
            source.backup(snapshot)
            result = snapshot.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0] != "ok":
                raise RuntimeError("Database integrity check failed; backup was not created.")
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(snapshot_path, "database/teacher_management.db")
            if UPLOAD_DIR.exists():
                for path in UPLOAD_DIR.rglob("*"):
                    if path.is_file():
                        archive.write(path, f"uploads/{path.relative_to(UPLOAD_DIR).as_posix()}")
    return archive_path


def restore_backup(archive_path: Path) -> Path:
    archive_path = archive_path.resolve()
    if not archive_path.is_file():
        raise FileNotFoundError(f"Backup archive not found: {archive_path}")
    if input(
        "Stop the app first. Type RESTORE to replace its database and uploaded files: "
    ) != "RESTORE":
        raise RuntimeError("Restore cancelled.")

    database_path = _database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with tempfile.TemporaryDirectory(dir=database_path.parent) as temp_directory:
        staging = Path(temp_directory)
        staged_database = staging / "teacher_management.db"
        staged_uploads = staging / "private_uploads"
        staged_uploads.mkdir()
        with zipfile.ZipFile(archive_path, "r") as archive:
            members = archive.infolist()
            if not any(item.filename == "database/teacher_management.db" for item in members):
                raise ValueError("Backup archive does not contain its SQLite database.")
            for member in members:
                relative = PurePosixPath(member.filename)
                mode = member.external_attr >> 16
                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                    or "\\" in member.filename
                    or any(":" in part for part in relative.parts)
                    or stat.S_ISLNK(mode)
                ):
                    raise ValueError("Backup archive contains an unsafe path.")
                if member.filename == "database/teacher_management.db":
                    target = staged_database
                elif relative.parts and relative.parts[0] == "uploads":
                    target = staged_uploads.joinpath(*relative.parts[1:])
                    if member.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                else:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member, "r") as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)

        with closing(sqlite3.connect(staged_database)) as restored:
            result = restored.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0] != "ok":
                raise RuntimeError("Restored database failed its integrity check.")

        safety_archive = (
            create_backup(BACKUP_DIR / f"before-restore-{timestamp}.zip")
            if database_path.is_file()
            else None
        )
        prior_database = database_path.with_name(
            f"{database_path.name}.before-restore-{timestamp}"
        )
        prior_uploads = UPLOAD_DIR.with_name(f"{UPLOAD_DIR.name}.before-restore-{timestamp}")
        moved_database = False
        moved_uploads = False
        try:
            if database_path.exists():
                database_path.replace(prior_database)
                moved_database = True
            if UPLOAD_DIR.exists():
                UPLOAD_DIR.replace(prior_uploads)
                moved_uploads = True
            database_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged_database, database_path)
            UPLOAD_DIR.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged_uploads, UPLOAD_DIR)
        except OSError:
            if moved_database:
                if database_path.exists():
                    database_path.replace(staging / "failed-restore.sqlite3")
                prior_database.replace(database_path)
            if moved_uploads:
                if UPLOAD_DIR.exists():
                    UPLOAD_DIR.replace(staging / "failed-restore-uploads")
                prior_uploads.replace(UPLOAD_DIR)
            raise
    previous_state = str(safety_archive) if safety_archive else "no previous database existed"
    print(f"Restored from {archive_path}. Previous state: {previous_state}.")
    return archive_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Back up or restore the local SQLite app.")
    parser.add_argument("action", choices=("backup", "restore"))
    parser.add_argument("archive", nargs="?", type=Path)
    args = parser.parse_args()
    if args.action == "backup":
        result = create_backup(args.archive)
        print(f"Backup created: {result}")
    else:
        if args.archive is None:
            parser.error("restore requires a backup archive path")
        restore_backup(args.archive)


if __name__ == "__main__":
    main()
