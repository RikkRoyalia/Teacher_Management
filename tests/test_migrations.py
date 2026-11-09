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
    def test_manager_notification_scope_migration_preserves_existing_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            database_path = root / "notifications.sqlite3"
            with closing(sqlite3.connect(database_path)) as connection:
                connection.executescript(
                    """
                    PRAGMA foreign_keys=ON;
                    CREATE TABLE departments (id INTEGER PRIMARY KEY);
                    CREATE TABLE users (id INTEGER PRIMARY KEY);
                    CREATE TABLE notifications (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        event_key VARCHAR(160) NOT NULL,
                        level VARCHAR(20) NOT NULL,
                        title VARCHAR(160) NOT NULL,
                        message TEXT NOT NULL,
                        target_view VARCHAR(40) NOT NULL,
                        target_id VARCHAR(80),
                        is_read BOOLEAN NOT NULL DEFAULT 0,
                        created_at DATETIME NOT NULL,
                        CONSTRAINT uq_notification_user_event UNIQUE (user_id, event_key)
                    );
                    CREATE INDEX ix_notifications_user_id ON notifications(user_id);
                    CREATE INDEX ix_notifications_user_created_at
                        ON notifications(user_id, created_at);
                    INSERT INTO departments (id) VALUES (1);
                    INSERT INTO users (id) VALUES (1);
                    INSERT INTO notifications (
                        id, user_id, event_key, level, title, message,
                        target_view, is_read, created_at
                    ) VALUES (
                        1, 1, 'existing-event', 'info', 'Existing', 'Preserve me',
                        'reports', 0, CURRENT_TIMESTAMP
                    );
                    CREATE TABLE alembic_version (
                        version_num VARCHAR(32) NOT NULL PRIMARY KEY
                    );
                    INSERT INTO alembic_version (version_num) VALUES ('20261109_0006');
                    """
                )

            database_url = f"sqlite:///{database_path.as_posix()}"
            engine, _ = create_database(database_url)
            try:
                with patch.dict(
                    "os.environ",
                    {"TEACHER_MANAGEMENT_BACKUP_DIR": str(root / "backups")},
                ):
                    migrate_database(database_url, engine)

                with engine.connect() as connection:
                    columns = {
                        row[1]
                        for row in connection.exec_driver_sql(
                            "PRAGMA table_info(notifications)"
                        )
                    }
                    self.assertIn("manager_faculty_id", columns)
                    self.assertEqual(
                        connection.exec_driver_sql(
                            "SELECT message FROM notifications WHERE id=1"
                        ).scalar_one(),
                        "Preserve me",
                    )
                    foreign_keys = connection.exec_driver_sql(
                        "PRAGMA foreign_key_list(notifications)"
                    ).all()
                    self.assertTrue(
                        any(
                            row[2] == "departments"
                            and row[3] == "manager_faculty_id"
                            and row[6] == "SET NULL"
                            for row in foreign_keys
                        )
                    )
                    indexes = {
                        row[1]
                        for row in connection.exec_driver_sql(
                            "PRAGMA index_list(notifications)"
                        )
                    }
                    self.assertIn(
                        "ix_notifications_user_manager_faculty", indexes
                    )
            finally:
                engine.dispose()

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
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY,
                        username VARCHAR(80) NOT NULL UNIQUE,
                        full_name VARCHAR(160) NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        role VARCHAR(20) NOT NULL CONSTRAINT ck_user_role CHECK (
                            role IN ('admin', 'hr', 'manager')
                        ),
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        failed_login_attempts INTEGER NOT NULL DEFAULT 0,
                        locked_until DATETIME,
                        created_at DATETIME NOT NULL
                    );
                    CREATE TABLE login_sessions (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        token_hash VARCHAR(64) NOT NULL UNIQUE,
                        csrf_token_hash VARCHAR(64) NOT NULL,
                        expires_at DATETIME NOT NULL,
                        created_at DATETIME NOT NULL
                    );
                    CREATE TABLE audit_logs (
                        id INTEGER PRIMARY KEY,
                        actor_id INTEGER REFERENCES users(id) ON DELETE RESTRICT,
                        action VARCHAR(80) NOT NULL,
                        entity_type VARCHAR(80) NOT NULL,
                        entity_id VARCHAR(80),
                        outcome VARCHAR(30) NOT NULL,
                        details TEXT,
                        created_at DATETIME NOT NULL
                    );
                    INSERT INTO departments (id, code, name) VALUES (1, 'IT', 'Information Technology');
                    INSERT INTO teachers (
                        id, employee_code, full_name, department_id, employment_status
                    ) VALUES (1, 'T001', 'Legacy Teacher', 1, 'active');
                    INSERT INTO checklist_items (code, label, category, is_required)
                    VALUES ('legacy-required', 'Existing required item', 'Legacy', 1);
                    INSERT INTO checklist_items (code, label, category, is_required)
                    VALUES ('legacy-optional', 'Existing optional item', 'Legacy', 0);
                    INSERT INTO users (
                        id, username, full_name, password_hash, role, created_at
                    ) VALUES (1, 'legacy-admin', 'Legacy Admin', 'hash', 'admin', CURRENT_TIMESTAMP);
                    INSERT INTO login_sessions (
                        id, user_id, token_hash, csrf_token_hash, expires_at, created_at
                    ) VALUES (1, 1, 'token', 'csrf', '2099-01-01', CURRENT_TIMESTAMP);
                    INSERT INTO audit_logs (
                        id, actor_id, action, entity_type, outcome, created_at
                    ) VALUES (1, 1, 'before_migration', 'user', 'success', CURRENT_TIMESTAMP);
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
                    self.assertEqual(
                        connection.exec_driver_sql(
                            "SELECT username FROM users WHERE id=1"
                        ).scalar_one(),
                        "legacy-admin",
                    )
                    self.assertEqual(
                        connection.exec_driver_sql(
                            "SELECT COUNT(*) FROM login_sessions"
                        ).scalar_one(),
                        1,
                    )
                    self.assertEqual(
                        connection.exec_driver_sql(
                            "SELECT COUNT(*) FROM audit_logs WHERE actor_id=1"
                        ).scalar_one(),
                        1,
                    )
                    document_table = connection.exec_driver_sql(
                        "SELECT sql FROM sqlite_master "
                        "WHERE type='table' AND name='evidence_documents'"
                    ).scalar_one()
                    self.assertIn("'withdrawn'", document_table)
                self.assertEqual(len(list(backup_path.glob("pre-migration-*.sqlite3"))), 1)
                migrate_database(database_url, engine)
                self.assertEqual(len(list(backup_path.glob("pre-migration-*.sqlite3"))), 1)
            finally:
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
