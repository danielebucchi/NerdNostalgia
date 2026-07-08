"""
API avvisi "nuovo arrivo" (category_alerts).

POST /api/alerts/            — pubblico (rate-limited + honeypot): iscrive
                               una email a una categoria (o a tutte).
GET  /api/alerts/unsubscribe — link nelle email: rimuove TUTTE le iscrizioni
                               dell'email se il token HMAC e' valido.
GET  /api/alerts/            — admin: lista iscrizioni.
DELETE /api/alerts/{id}      — admin: rimuove una iscrizione.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from helpers.auth import require_admin
from models.db import Category, CategoryAlert, User
from utils.category_alerts import verify_unsubscribe_token
from utils.limiter import limiter
from utils.session import get_db

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class AlertSubscribeRequest(BaseModel):
    email: EmailStr
    category_id: Optional[int] = None  # None = tutte le categorie
    # Honeypot: i bot lo compilano, gli umani non lo vedono.
    website: Optional[str] = Field(None, max_length=500)


class AlertResponse(BaseModel):
    id: int
    email: str
    category_id: Optional[int]
    category_name: Optional[str] = None
    created_at: Optional[str] = None


def _to_response(sub: CategoryAlert) -> AlertResponse:
    return AlertResponse(
        id=sub.id,
        email=sub.email,
        category_id=sub.category_id,
        category_name=sub.category.name if sub.category else None,
        created_at=sub.created_at.isoformat() if sub.created_at else None,
    )


@router.post("/", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute;20/hour")
def subscribe(
    payload: AlertSubscribeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Iscrizione pubblica. Idempotente: se (email, categoria) esiste gia',
    ritorna quella. Honeypot compilato → finto successo."""
    email_norm = str(payload.email).lower().strip()

    if payload.website:
        return AlertResponse(id=0, email=email_norm, category_id=payload.category_id)

    if payload.category_id is not None:
        cat = db.query(Category).filter(Category.id == payload.category_id).first()
        if not cat:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Categoria {payload.category_id} non trovata",
            )

    existing = (
        db.query(CategoryAlert)
        .filter(
            CategoryAlert.email == email_norm,
            CategoryAlert.category_id.is_(None)
            if payload.category_id is None
            else CategoryAlert.category_id == payload.category_id,
        )
        .first()
    )
    if existing:
        return _to_response(existing)

    sub = CategoryAlert(email=email_norm, category_id=payload.category_id)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return _to_response(sub)


@router.get("/unsubscribe", response_class=HTMLResponse)
def unsubscribe(
    email: str,
    token: str,
    db: Session = Depends(get_db),
):
    """Rimuove tutte le iscrizioni dell'email. Link diretto dalle email,
    quindi risponde con una pagina HTML minimale invece che JSON."""
    if not verify_unsubscribe_token(email, token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token non valido",
        )
    email_norm = email.lower().strip()
    removed = (
        db.query(CategoryAlert)
        .filter(CategoryAlert.email == email_norm)
        .delete(synchronize_session=False)
    )
    db.commit()
    return HTMLResponse(
        "<html><body style='font-family:sans-serif;text-align:center;"
        "padding-top:60px'>"
        "<h2>✓ Disiscrizione completata</h2>"
        f"<p>Non riceverai piu' avvisi ({removed} iscrizioni rimosse).</p>"
        "</body></html>"
    )


@router.get("/", response_model=List[AlertResponse])
def list_subscriptions(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    subs = db.query(CategoryAlert).order_by(CategoryAlert.id.desc()).all()
    return [_to_response(s) for s in subs]


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(
    alert_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    sub = db.query(CategoryAlert).filter(CategoryAlert.id == alert_id).first()
    if not sub:
        raise HTTPException(404, f"Iscrizione {alert_id} non trovata")
    db.delete(sub)
    db.commit()
    return None
