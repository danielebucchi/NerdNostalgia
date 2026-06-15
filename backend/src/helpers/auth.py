"""
Dependency FastAPI per autenticazione e autorizzazione.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from helpers.user import UserHelper, get_user_helper
from models.db import User, UserRole
from utils.security import TokenError, safe_decode
from utils.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_helper: UserHelper = Depends(get_user_helper),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenziali non valide",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = safe_decode(token)
    except TokenError:
        raise credentials_exc

    username = payload.get("sub")
    if not username:
        raise credentials_exc

    user = user_helper.get("username", username)
    if not user:
        raise credentials_exc
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utente disattivato",
        )
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo gli admin possono eseguire questa operazione",
        )
    return current_user
