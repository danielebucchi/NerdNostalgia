"""
Endpoint di autenticazione.

I clienti riusano la stessa tabella e lo stesso login dell'admin: cambia il
ruolo (USER contro ADMIN) e quindi cosa possono fare. Si registrano con
l'email, che diventa anche lo username: cosi' accedono con l'indirizzo e non
devono inventarsi un nome da ricordare.

NB: NIENTE `from __future__ import annotations` (vedi api/orders.py).
"""
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from helpers.auth import get_current_user
from helpers.user import UserHelper, get_user_helper
from models.db import Order, User, UserRole
from models.entities.auth import TokenResponse
from models.entities.user import UserResponse
from utils.limiter import limiter
from utils.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    hash_password,
    verify_password,
)
from utils.session import get_db

LOGGER = logging.getLogger("auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_helper: UserHelper = Depends(get_user_helper),
):
    """Login via form-data (compatibile OAuth2 password flow)."""
    user = user_helper.get("username", form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username o password errati",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utente disattivato",
        )

    token = create_access_token(subject=user.username, role=user.role.value)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Restituisce l'utente autenticato."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at.isoformat(),
        updated_at=current_user.updated_at.isoformat(),
    )


class RegisterRequest(BaseModel):
    """Registrazione cliente.

    Il consenso promozionale e' un campo a parte e parte da False: il GDPR
    vuole che sia libero e distinto dalla creazione dell'account, quindi non
    si puo' dedurre dal fatto che uno si sia iscritto.
    """
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)
    marketing_consent: bool = False


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute;30/hour")
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Crea un account cliente e lo autentica subito.

    Chi si registra ha appena finito di scrivere email e password: chiedergli
    di rifarlo per accedere e' un passaggio inutile.
    """
    email = str(payload.email).strip().lower()

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=409,
            detail="Esiste già un account con questa email. Prova ad accedere.",
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user = User(
        username=email,            # si accede con l'email
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=(payload.full_name or "").strip() or None,
        role=UserRole.USER,
        is_active=True,
        marketing_consent=bool(payload.marketing_consent),
        marketing_consent_at=now if payload.marketing_consent else None,
        unsubscribe_token=secrets.token_urlsafe(24),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Ordini fatti da ospite con la stessa email: glieli attacchiamo al
    # profilo, cosi' li ritrova nello storico invece di non vederli piu'.
    recuperati = (
        db.query(Order)
        .filter(Order.buyer_email == email, Order.user_id.is_(None))
        .update({Order.user_id: user.id}, synchronize_session=False)
    )
    if recuperati:
        db.commit()
        LOGGER.info("Collegati %s ordini da ospite a %s", recuperati, email)

    # In background: chi si registra non deve guardare uno spinner mentre
    # aspettiamo che Gmail risponda.
    from utils import mailer
    mailer.welcome(user.id)

    token = create_access_token(subject=user.username, role=user.role.value)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
