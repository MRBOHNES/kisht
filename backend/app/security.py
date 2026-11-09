from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

COOKIE_NAME = "kisht_session"
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


BCRYPT_MAX_BYTES = 72


def verify_password(password: str, password_hash: str) -> bool:
    # bcrypt raises on longer input; no stored hash can match such a password anyway
    if len(password.encode()) > BCRYPT_MAX_BYTES:
        return False
    return bcrypt.checkpw(password.encode(), password_hash.encode())


# Verified against when the email is unknown, so response time doesn't reveal which emails exist.
DUMMY_HASH = hash_password("not-a-real-password")


def make_token(user_id: int, role: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.session_hours)
    return jwt.encode({"sub": str(user_id), "role": role, "exp": expires}, settings.jwt_secret, ALGORITHM)


def read_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
