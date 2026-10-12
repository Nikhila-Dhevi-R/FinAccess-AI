"""Account signup, MPIN hashing, and bearer-token authentication helpers."""

import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from config import get_settings
from database import get_db
from models import User


PASSWORD_CONTEXT = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
BEARER_SCHEME = HTTPBearer(auto_error=False)
USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,31}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MPIN_PATTERN = re.compile(r"^\d{6}$")


class AccountAuthError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def normalize_username(value: str) -> str:
    return value.strip().casefold()


def normalize_email(value: str) -> str:
    return value.strip().casefold()


def hash_mpin(mpin: str) -> str:
    return PASSWORD_CONTEXT.hash(mpin)


def verify_mpin(mpin: str, mpin_hash: str) -> bool:
    return bool(mpin_hash) and PASSWORD_CONTEXT.verify(mpin, mpin_hash)


def _validate_signup(username: str, email: str, mpin: str, mpin_confirmation: str) -> tuple[str, str]:
    normalized_username = normalize_username(username)
    normalized_email = normalize_email(email)
    if not USERNAME_PATTERN.fullmatch(normalized_username):
        raise AccountAuthError(
            "invalid_username",
            "Username must be 3–32 characters using letters, numbers, dot, dash, or underscore.",
        )
    if not EMAIL_PATTERN.fullmatch(normalized_email):
        raise AccountAuthError("invalid_email", "Enter a valid email address.")
    if not MPIN_PATTERN.fullmatch(mpin):
        raise AccountAuthError("invalid_mpin", "MPIN must contain exactly 6 digits.")
    if mpin != mpin_confirmation:
        raise AccountAuthError("mpin_mismatch", "The MPIN entries do not match.")
    return normalized_username, normalized_email


def create_account(
    db: DBSession,
    username: str,
    email: str,
    mpin: str,
    mpin_confirmation: str,
) -> User:
    normalized_username, normalized_email = _validate_signup(username, email, mpin, mpin_confirmation)
    if db.query(User).filter(func.lower(User.username) == normalized_username).first():
        raise AccountAuthError("username_taken", "That username is already registered.", 409)
    if db.query(User).filter(func.lower(User.email) == normalized_email).first():
        raise AccountAuthError("email_taken", "That email is already registered.", 409)

    user = User(
        id=str(uuid.uuid4()),
        username=normalized_username,
        email=normalized_email,
        mpin_hash=hash_mpin(mpin),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_account(db: DBSession, username: str, mpin: str) -> User:
    normalized_username = normalize_username(username)
    user = db.query(User).filter(func.lower(User.username) == normalized_username).first()
    if not user or not user.mpin_hash or not verify_mpin(mpin, user.mpin_hash):
        raise AccountAuthError("invalid_credentials", "Username or MPIN is incorrect.", 401)
    return user


def create_access_token(user: User) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.AUTH_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user.id, "exp": expires_at}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def _auth_failure() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "invalid_token", "message": "Your login session is invalid or expired."},
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(BEARER_SCHEME),
    db: DBSession = Depends(get_db),
) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise _auth_failure()
    settings = get_settings()
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise JWTError("missing subject")
    except (JWTError, ValueError):
        raise _auth_failure()
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.username or not user.email or not user.mpin_hash:
        raise _auth_failure()
    return user
