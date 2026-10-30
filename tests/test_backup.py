import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from app import backup


class LocalBackupTests(unittest.TestCase):
    def test_backup_and_confirmed_restore_preserve_database_and_uploads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            database_path = root / "teacher_management.db"
            uploads = root / "private_uploads"
            backups = root / ".backups"
            uploads.mkdir()
            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute("CREATE TABLE sample (value TEXT)")
                connection.execute("INSERT INTO sample (value) VALUES ('before')")
                connection.commit()
            (uploads / "proof.pdf").write_bytes(b"old evidence")

            with (
                patch.object(backup, "DATABASE_URL", f"sqlite:///{database_path.as_posix()}"),
                patch.object(backup, "UPLOAD_DIR", uploads),
                patch.object(backup, "BACKUP_DIR", backups),
            ):
                archive_path = backup.create_backup(root / "test-backup.zip")
                with closing(sqlite3.connect(database_path)) as connection:
                    connection.execute("UPDATE sample SET value='after'")
                    connection.commit()
                (uploads / "proof.pdf").write_bytes(b"new evidence")

                with patch("builtins.input", return_value="RESTORE"):
                    backup.restore_backup(archive_path)

            with closing(sqlite3.connect(database_path)) as restored:
                value = restored.execute("SELECT value FROM sample").fetchone()[0]
            self.assertEqual(value, "before")
            self.assertEqual((uploads / "proof.pdf").read_bytes(), b"old evidence")
            self.assertTrue(list(root.glob("teacher_management.db.before-restore-*")))
            self.assertTrue(list(root.glob("private_uploads.before-restore-*")))


if __name__ == "__main__":
    unittest.main()
