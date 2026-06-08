import hashlib
import hmac
import secrets
import string
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Header, HTTPException, status
from jose import JWTError, jwt

from app.config import get_settings

ALGORITHM = "HS256"


def create_room_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str | None, password_hash: str | None) -> bool:
    if not password_hash:
        return True
    if not password:
        return False
    try:
        algorithm, salt, expected = password_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return hmac.compare_digest(digest.hex(), expected)


def create_session_token(participant_id: str, room_id: str, is_owner: bool) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": participant_id,
        "room_id": room_id,
        "is_owner": is_owner,
        "iat": now,
        "exp": now + timedelta(days=14),
    }
    return jwt.encode(payload, settings.session_secret, algorithm=ALGORITHM)


def decode_session_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.session_secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from exc


def bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session")
    return authorization.split(" ", 1)[1].strip()
