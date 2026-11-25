"""Newsletter dei nuovi arrivi: stato e anteprima per l'admin (l'invio vero
lo fa lo scheduler il venerdi', vedi utils/newsletter.py)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from helpers.auth import require_admin
from helpers.setting import SettingHelper
from models.db import User
from utils import newsletter
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
