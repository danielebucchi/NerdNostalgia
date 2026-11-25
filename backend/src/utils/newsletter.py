"""
Newsletter settimanale dei nuovi arrivi.

Il venerdi' alle 18 i clienti che hanno dato il consenso promozionale
ricevono gli articoli pubblicati nella settimana: e' il motivo per tornare
sul sito. Parte solo se accesa in Impostazioni (newsletter_enabled), solo
se ci sono novita', e al massimo una volta a settimana. Ogni email porta il
link per revocare il consenso (/disiscriviti), come la legge chiede.

Al massimo MAX_DESTINATARI per giro: il freno sugli invii (email_guard)
tiene la quota SMTP per le conferme d'ordine, e una newsletter non deve
mangiarsela.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from models.db import Article, ArticleStatus, User

LOGGER = logging.getLogger("newsletter")

GIORNI = 7
MAX_ARTICOLI = 12
MAX_DESTINATARI = 100
CHIAVE_ACCESA = "newsletter_enabled"
CHIAVE_ULTIMA = "newsletter_last_sent"


def _ora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def nuovi_arrivi(db: Session, giorni: int = GIORNI) -> List[Article]:
    dal = _ora() - timedelta(days=giorni)
    return (db.query(Article)
            .filter(Article.status == ArticleStatus.PUBLISHED,
                    Article.reserved_order_id.is_(None),
                    Article.published_at >= dal)
            .order_by(Article.published_at.desc())
            .limit(MAX_ARTICOLI).all())


def destinatari(db: Session) -> List[User]:
    return (db.query(User)
            .filter(User.marketing_consent.is_(True), User.is_active.is_(True), User.email.isnot(None))
            .order_by(User.id).limit(MAX_DESTINATARI).all())


def _foto(a: Article) -> Optional[str]:
    from utils.category_alerts import _api_url
    url = (a.images or [None])[0]
    if not url:
        return None
    return url if url.startswith("http") else f"{_api_url()}/{url.lstrip('/')}"


def _corpo(articoli: List[Article], link_revoca: str) -> Dict[str, str]:
    from utils.email import _h, _site_url
    site = _site_url()
    righe_txt, celle = [], []
    for a in articoli:
        prezzo = f"{float(a.price):.2f} €".replace(".", ",")
        link = f"{site}/articles/{a.id}"
        righe_txt.append(f"- {a.title} — {prezzo}\n  {link}")
        foto = _foto(a)
        img = (f'<img src="{_h(foto)}" alt="" width="140" style="border-radius:8px;display:block;margin:auto">'
               if foto else "")
        celle.append(
            f'<td style="width:50%;padding:8px;vertical-align:top;text-align:center">'
            f'<a href="{_h(link)}" style="color:#3d2a5c;text-decoration:none">{img}'
            f'<div style="font-size:0.9em;margin-top:6px">{_h(a.title)}</div>'
            f'<strong style="color:#e879a8">{_h(prezzo)}</strong></a></td>')
    tabella = "".join(f"<tr>{''.join(celle[i:i + 2])}</tr>" for i in range(0, len(celle), 2))
    testo = ("Ecco i nuovi arrivi della settimana su NerdNostalgia:\n\n" + "\n".join(righe_txt)
             + f"\n\nTutto il catalogo: {site}\n\n"
             f"Ricevi questa email perche' hai acconsentito alle comunicazioni promozionali.\n"
             f"Per non riceverle piu': {link_revoca}\n")
    html = f"""<html><body style="font-family:sans-serif;max-width:640px;margin:auto;color:#3d2a5c">
  <h2 style="color:#e879a8">Nuovi arrivi della settimana</h2>
  <table style="width:100%;border-collapse:collapse">{tabella}</table>
  <p style="text-align:center;margin:20px 0"><a href="{_h(site)}" style="background:#e879a8;color:#fff;padding:10px 18px;border-radius:20px;text-decoration:none">Tutto il catalogo</a></p>
  <p style="color:#888;font-size:0.85em">Ricevi questa email perche' hai acconsentito alle comunicazioni promozionali.
  <a href="{_h(link_revoca)}" style="color:#888">Revoca il consenso</a>.</p>
</body></html>"""
    return {"text": testo, "html": html}


def _link_revoca(db: Session, user: User) -> str:
    from utils.email import _site_url
    if not user.unsubscribe_token:
        user.unsubscribe_token = secrets.token_urlsafe(32)
        db.commit()
    return f"{_site_url()}/disiscriviti?t={user.unsubscribe_token}"


def invia(db: Session, solo_a: Optional[str] = None) -> Dict[str, object]:
    """Manda la newsletter. Con `solo_a` (anteprima) arriva solo a quell'indirizzo
    e non conta come invio della settimana."""
    from utils.email import send_email
    articoli = nuovi_arrivi(db)
    if not articoli:
        return {"inviate": 0, "articoli": 0, "motivo": "nessun nuovo arrivo questa settimana"}
    oggetto = f"Nuovi arrivi su NerdNostalgia: {len(articoli)} pezzi questa settimana"
    if solo_a:
        corpo = _corpo(articoli, "(link per revocare il consenso)")
        ok = send_email(to=solo_a, subject=f"[Anteprima] {oggetto}", text_body=corpo["text"], html_body=corpo["html"])
        return {"inviate": int(bool(ok)), "articoli": len(articoli), "anteprima": True}
    inviate = 0
    for user in destinatari(db):
        corpo = _corpo(articoli, _link_revoca(db, user))
        if send_email(to=user.email, subject=oggetto, text_body=corpo["text"], html_body=corpo["html"]):
            inviate += 1
    LOGGER.info("Newsletter: %d email, %d articoli", inviate, len(articoli))
    return {"inviate": inviate, "articoli": len(articoli)}


def run_settimanale(db: Session) -> Optional[Dict[str, object]]:
    """Il giro del venerdi': solo se accesa e non gia' partita in settimana."""
    from helpers.setting import SettingHelper
    impostazioni = SettingHelper(db=db)
    if (impostazioni.get_value(CHIAVE_ACCESA) or "").strip().lower() != "true":
        return None
    ultima = (impostazioni.get_value(CHIAVE_ULTIMA) or "").strip()
    if ultima:
        try:
            if _ora() - datetime.fromisoformat(ultima) < timedelta(days=6):
                return None
        except ValueError:
            pass
    esito = invia(db)
    impostazioni.upsert(CHIAVE_ULTIMA, _ora().isoformat(timespec="seconds"))
    return esito
