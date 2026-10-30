import hashlib
import hmac
import secrets
from collections.abc import Callable, Generator
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LoginSession, User

SESSION_COOKIE = "teacher_management_session"
CSRF_COOKIE = "teacher_management_csrf"
SESSION_DURATION = timedelta(hours=8)
PASSWORD_ITERATIONS = 600_000
LOCK_AFTER_FAILURES = 5
LOCK_DURATION = timedelta(minutes=15)


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, expected = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(derived.hex(), expected)


def issue_session(db: Session, user: User) -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    db.add(
        LoginSession(
            user_id=user.id,
            token_hash=hash_secret(token),
            csrf_token_hash=hash_secret(csrf_token),
            created_at=now,
            expires_at=now + SESSION_DURATION,
        )
    )
    return token, csrf_token


def get_db(request: Request) -> Generator[Session, None, None]:
    with request.app.state.session_factory() as session:
        yield session


DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(request: Request, db: DbSession) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    login_session = db.scalar(
        select(LoginSession).where(LoginSession.token_hash == hash_secret(token))
    )
    now = datetime.now(timezone.utc)
    if login_session is None or _as_utc(login_session.expires_at) <= now:
        if login_session is not None:
            db.delete(login_session)
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please sign in again.",
        )

    user = db.get(User, login_session.user_id)
    if user is None or not user.is_active:
        db.delete(login_session)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive.",
        )
    request.state.login_session = login_session
    return user


def require_roles(*roles: str) -> Callable:
    def authorize(
        request: Request,
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if roles and user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            login_session: LoginSession = request.state.login_session
            supplied = request.headers.get("X-CSRF-Token", "")
            if not hmac.compare_digest(
                hash_secret(supplied), login_session.csrf_token_hash
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="A valid CSRF token is required.",
                )
        return user

    return authorize


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
