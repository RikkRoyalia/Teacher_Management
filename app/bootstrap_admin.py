from getpass import getpass
import re

from sqlalchemy import func, select

from app.audit import record_audit
from app.database import DATABASE_URL, create_database, migrate_database
from app.models import User
from app.security import hash_password


def main() -> None:
    engine, session_factory = create_database(DATABASE_URL)
    try:
        migrate_database(DATABASE_URL, engine)
        with session_factory() as db:
            existing_users = db.scalar(select(func.count()).select_from(User)) or 0
            if existing_users:
                raise SystemExit(
                    "Accounts already exist. Use the account management screen instead."
                )
            username = input("Initial administrator username: ").strip().lower()
            full_name = input("Administrator full name: ").strip()
            password = getpass("Password (at least 12 characters): ")
            confirmation = getpass("Confirm password: ")
            if len(password) < 12:
                raise SystemExit("Password must contain at least 12 characters.")
            if password != confirmation:
                raise SystemExit("Passwords do not match.")
            if not username or not full_name:
                raise SystemExit("Username and full name are required.")
            if not re.fullmatch(r"[a-z0-9._-]{3,80}", username):
                raise SystemExit(
                    "Username must be 3-80 characters using lowercase letters, numbers, '.', '_' or '-'."
                )

            administrator = User(
                username=username,
                full_name=full_name,
                password_hash=hash_password(password),
                role="admin",
            )
            db.add(administrator)
            db.flush()
            record_audit(
                db,
                administrator,
                "initial_administrator_created",
                "user",
                administrator.id,
            )
            db.commit()
            print("Initial administrator created. Keep the password private.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
