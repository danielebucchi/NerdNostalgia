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
        marketing_consent_at=now,
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


# ---------------------------------------------------------------------------
# Consenso promozionale
#
# Due strade per la stessa cosa, perche' servono a due momenti diversi: il
# link in fondo alle email (token, niente login — chi vuole smettere di
# riceverle non deve prima ricordarsi la password) e l'interruttore nel
# profilo, per chi e' gia' dentro.
#
# `marketing_consent_at` registra QUANDO la spunta si e' mossa l'ultima
# volta, in un verso o nell'altro: la data da sola non dimostra niente, ma
# insieme al flag dice sia quando ha accettato sia quando ha revocato, che
# e' quello che serve se un domani qualcuno contesta un invio.
# ---------------------------------------------------------------------------


class ConsentRequest(BaseModel):
    """Il nuovo valore della spunta. False disiscrive, True riscrive."""
    marketing_consent: bool


class UnsubscribeRequest(ConsentRequest):
    # Il token e' la credenziale: chi ce l'ha ha ricevuto l'email, e tanto
    # basta. Non chiediamo anche l'indirizzo, che renderebbe il link
    # indovinabile da chi conosce l'email di qualcun altro.
    token: str = Field(..., min_length=8, max_length=64)


class ConsentResponse(BaseModel):
    email: str
    marketing_consent: bool


def _email_offuscata(email: str) -> str:
    """`mario.rossi@gmail.com` -> `ma***@gmail.com`.

    La pagina di disiscrizione deve far dire "si', e' il mio indirizzo"
    senza esporre l'email per intero: il link gira nella posta, e finisce
    nella cronologia del browser e nei log di chi sta in mezzo.
    """
    local, _, dominio = email.partition("@")
    if not dominio:
        return "***"
    visibile = local[:2] if len(local) > 2 else local[:1]
    return f"{visibile}***@{dominio}"


def _applica_consenso(user: User, consenso: bool) -> None:
    user.marketing_consent = consenso
    user.marketing_consent_at = datetime.now(timezone.utc).replace(tzinfo=None)
    # Account nati prima del consenso (o creati a mano) possono non avere
    # ancora un token: senza, il link in fondo alla prossima email non
    # porterebbe da nessuna parte.
    if consenso and not user.unsubscribe_token:
        user.unsubscribe_token = secrets.token_urlsafe(24)


@router.post("/unsubscribe", response_model=ConsentResponse)
@limiter.limit("30/hour")
def unsubscribe(
    payload: UnsubscribeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Disiscrizione (o ripensamento) dal link nelle email, senza login."""
    user = (
        db.query(User)
        .filter(User.unsubscribe_token == payload.token)
        .first()
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link non valido. Se vuoi smettere di ricevere le email, "
                   "scrivimi e ci penso io.",
        )

    _applica_consenso(user, payload.marketing_consent)
    db.commit()
    LOGGER.info(
        "Consenso promozionale -> %s per utente %s (da link email)",
        payload.marketing_consent,
        user.id,
    )
    return ConsentResponse(
        email=_email_offuscata(user.email),
        marketing_consent=user.marketing_consent,
    )


@router.get("/me/marketing-consent", response_model=ConsentResponse)
def get_marketing_consent(current_user: User = Depends(get_current_user)):
    return ConsentResponse(
        email=current_user.email,
        marketing_consent=bool(current_user.marketing_consent),
    )


@router.put("/me/marketing-consent", response_model=ConsentResponse)
def set_marketing_consent(
    payload: ConsentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """L'interruttore nel profilo. L'email di benvenuto promette che la
    spunta si trova li': questo e' quello che mantiene la promessa."""
    _applica_consenso(current_user, payload.marketing_consent)
    db.commit()
    return ConsentResponse(
        email=current_user.email,
        marketing_consent=current_user.marketing_consent,
    )
