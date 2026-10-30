import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import select

from app.database import create_database, migrate_database
from app.models import Teacher


class LegacyDatabaseMigrationTests(unittest.TestCase):
    def test_existing_teacher_rows_survive_upgrade_and_are_backed_up(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            database_path = root / "legacy.sqlite3"
            backup_path = root / "backups"
            with closing(sqlite3.connect(database_path)) as connection:
                connection.executescript(
                    """
                    CREATE TABLE departments (
                        id INTEGER PRIMARY KEY,
                        code VARCHAR(30) NOT NULL UNIQUE,
                        name VARCHAR(120) NOT NULL,
                        description VARCHAR(500),
                        is_active BOOLEAN NOT NULL DEFAULT 1
                    );
                    CREATE TABLE teachers (
                        id INTEGER PRIMARY KEY,
                        employee_code VARCHAR(40) NOT NULL UNIQUE,
                        full_name VARCHAR(160) NOT NULL,
                        date_of_birth DATE,
                        gender VARCHAR(40),
                        email VARCHAR(254),
                        phone VARCHAR(30),
                        address VARCHAR(300),
                        department_id INTEGER NOT NULL,
                        academic_degree VARCHAR(80),
                        academic_title VARCHAR(80),
                        employment_status VARCHAR(20) NOT NULL DEFAULT 'active'
                    );
                    CREATE TABLE checklist_items (
                        id INTEGER PRIMARY KEY,
                        code VARCHAR(80) NOT NULL UNIQUE,
                        label VARCHAR(200) NOT NULL,
                        category VARCHAR(80) NOT NULL,
                        is_required BOOLEAN NOT NULL DEFAULT 0,
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        is_sensitive BOOLEAN NOT NULL DEFAULT 0
                    );
                    INSERT INTO departments (id, code, name) VALUES (1, 'IT', 'Information Technology');
                    INSERT INTO teachers (
                        id, employee_code, full_name, department_id, employment_status
                    ) VALUES (1, 'T001', 'Legacy Teacher', 1, 'active');
                    INSERT INTO checklist_items (code, label, category, is_required)
                    VALUES ('legacy-required', 'Existing required item', 'Legacy', 1);
                    INSERT INTO checklist_items (code, label, category, is_required)
                    VALUES ('legacy-optional', 'Existing optional item', 'Legacy', 0);
                    """
                )

            database_url = f"sqlite:///{database_path.as_posix()}"
            engine, _ = create_database(database_url)
            try:
                with patch.dict(
                    "os.environ",
                    {"TEACHER_MANAGEMENT_BACKUP_DIR": str(backup_path)},
                ):
                    migrate_database(database_url, engine)

                with engine.connect() as connection:
                    teacher = connection.execute(
                        select(Teacher).where(Teacher.id == 1)
                    ).one()
                    self.assertEqual(teacher.full_name, "Legacy Teacher")
                    checklist_count = connection.exec_driver_sql(
                        "SELECT COUNT(*) FROM checklist_items"
                    ).scalar_one()
                    self.assertEqual(checklist_count, 23)
                    requirement_counts = dict(
                        connection.exec_driver_sql(
                            "SELECT status, COUNT(*) FROM teacher_checklist_requirements "
                            "GROUP BY status"
                        ).all()
                    )
                    self.assertEqual(requirement_counts["review"], 18)
                    self.assertEqual(requirement_counts["optional"], 4)
                    self.assertEqual(requirement_counts["required"], 1)
                    legacy_classifications = dict(
                        connection.exec_driver_sql(
                            "SELECT code, classification FROM checklist_items "
                            "WHERE code LIKE 'legacy-%'"
                        ).all()
                    )
                    self.assertEqual(legacy_classifications["legacy-required"], "required")
                    self.assertEqual(legacy_classifications["legacy-optional"], "optional")
                    self.assertTrue(
                        connection.exec_driver_sql(
                            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'"
                        ).first()
                    )
                self.assertEqual(len(list(backup_path.glob("pre-migration-*.sqlite3"))), 1)
                migrate_database(database_url, engine)
                self.assertEqual(len(list(backup_path.glob("pre-migration-*.sqlite3"))), 1)
            finally:
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
