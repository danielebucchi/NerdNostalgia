"""
Hashing password e gestione JWT.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
# Default 7 giorni: admin single-user usato da telefono — il token da 60min
# buttava fuori a meta' catalogazione. Override via JWT_EXPIRE_MINUTES.
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", str(60 * 24 * 7)))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {"sub": subject, "role": role, "iat": now, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decodifica e valida un JWT. Solleva JWTError se invalido o scaduto."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


class TokenError(Exception):
    pass


def safe_decode(token: str) -> dict:
    try:
        return decode_access_token(token)
    except JWTError as exc:
        raise TokenError(str(exc)) from exc
