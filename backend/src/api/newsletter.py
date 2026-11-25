"""Newsletter dei nuovi arrivi: iscrizione dal footer (pubblica, con
conferma via email), stato e anteprima per l'admin. L'invio vero lo fa lo
scheduler il venerdi', vedi utils/newsletter.py. La disiscrizione passa da
/api/auth/unsubscribe, lo stesso link per clienti e iscritti."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import status as http
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from helpers.auth import require_admin
from helpers.setting import SettingHelper
from models.db import User
from utils import newsletter
from utils.limiter import limiter
from utils.session import get_db

router = APIRouter(prefix="/api/newsletter", tags=["newsletter"])


@router.get("/status")
def status(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    impostazioni = SettingHelper(db=db)
    return {
        "enabled": (impostazioni.get_value(newsletter.CHIAVE_ACCESA) or "").lower() == "true",
        "last_sent": impostazioni.get_value(newsletter.CHIAVE_ULTIMA) or None,
        "recipients": len(newsletter.destinatari(db)),
        "new_articles": len(newsletter.nuovi_arrivi(db)),
    }


@router.post("/preview")
def preview(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """La newsletter di questa settimana, solo all'indirizzo admin."""
    from utils.email import _config
    return newsletter.invia(db, solo_a=_config()["to_admin"])


class IscrizioneRequest(BaseModel):
    email: EmailStr
    # La spunta del consenso: senza, niente iscrizione (art. 7 GDPR).
    consent: bool = False
    # Honeypot: i bot lo compilano, gli umani non lo vedono.
    website: Optional[str] = Field(None, max_length=500)


class ConfermaRequest(BaseModel):
    token: str = Field(..., min_length=8, max_length=64)


@router.post("/subscribe")
@limiter.limit("5/minute;20/hour")
def subscribe(payload: IscrizioneRequest, request: Request, db: Session = Depends(get_db)):
    """Risponde sempre uguale, iscritto o no: non deve dire a chi prova
    indirizzi a caso quali sono gia' nella lista."""
    if not payload.consent:
        raise HTTPException(status_code=http.HTTP_400_BAD_REQUEST,
                            detail="Per iscriversi serve il consenso a ricevere la newsletter.")
    if not payload.website:
        newsletter.iscrivi(db, str(payload.email))
    return {"ok": True}


@router.post("/confirm")
@limiter.limit("30/hour")
def confirm(payload: ConfermaRequest, request: Request, db: Session = Depends(get_db)):
    """POST e non GET: le anteprime dei client di posta aprono i link da sole."""
    from api.auth import _email_offuscata
    iscritto = newsletter.conferma(db, payload.token)
    if iscritto is None:
        raise HTTPException(status_code=http.HTTP_404_NOT_FOUND,
                            detail="Link non valido o scaduto: si iscriva di nuovo dal fondo del sito.")
    return {"email": _email_offuscata(iscritto.email)}
