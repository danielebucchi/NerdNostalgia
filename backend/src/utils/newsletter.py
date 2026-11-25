"""
Newsletter settimanale dei nuovi arrivi.

Il venerdi' alle 18 i clienti che hanno dato il consenso promozionale, e
chi si e' iscritto dal footer e ha confermato dal link nell'email, ricevono gli articoli pubblicati nella settimana: e' il motivo per tornare
sul sito. Parte solo se accesa in Impostazioni (newsletter_enabled), solo
se ci sono novita', e al massimo una volta a settimana. Ogni email porta il
link per revocare il consenso (/disiscriviti), come la legge chiede.

Al massimo MAX_DESTINATARI per giro: il freno sugli invii (email_guard)
tiene la quota SMTP per le conferme d'ordine, e una newsletter non deve
mangiarsela.
"""
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from models.db import Article, ArticleStatus, NewsletterSubscriber, User

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


@dataclass
class Destinatario:
    email: str
    token_revoca: str


def destinatari(db: Session) -> List[Destinatario]:
    """Prima i clienti con il consenso, poi gli iscritti confermati dal
    footer; un indirizzo che e' in tutti e due riceve una email sola."""
    elenco: List[Destinatario] = []
    visti = set()
    clienti = (db.query(User)
               .filter(User.marketing_consent.is_(True), User.is_active.is_(True), User.email.isnot(None))
               .order_by(User.id).all())
    for user in clienti:
        if not user.unsubscribe_token:
            user.unsubscribe_token = secrets.token_urlsafe(32)
            db.commit()
        elenco.append(Destinatario(user.email, user.unsubscribe_token))
        visti.add(user.email.lower())
    iscritti = (db.query(NewsletterSubscriber)
                .filter(NewsletterSubscriber.confirmed_at.isnot(None),
                        NewsletterSubscriber.revoked_at.is_(None))
                .order_by(NewsletterSubscriber.id).all())
    for iscritto in iscritti:
        if iscritto.email.lower() not in visti:
            elenco.append(Destinatario(iscritto.email, iscritto.unsubscribe_token))
            visti.add(iscritto.email.lower())
    return elenco[:MAX_DESTINATARI]


def _foto(a: Article) -> Optional[str]:
    from utils.category_alerts import _api_url
    url = (a.images or [None])[0]
    if not url:
        return None
    return url if url.startswith("http") else f"{_api_url()}/{url.lstrip('/')}"


# Il gruppo Telegram: i nuovi arrivi li annuncia il bot ogni giorno, la
# newsletter li riassume una volta a settimana.
TELEGRAM_URL = "https://t.me/NerdNostalgia"


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
             + f"\n\nTutto il catalogo: {site}\n"
             f"I nuovi arrivi in tempo reale, scambi e domande sul gruppo Telegram: {TELEGRAM_URL}\n\n"
             f"Ricevi questa email perche' hai acconsentito alle comunicazioni promozionali.\n"
             f"Per non riceverle piu': {link_revoca}\n")
    html = f"""<html><body style="font-family:sans-serif;max-width:640px;margin:auto;color:#3d2a5c">
  <h2 style="color:#e879a8">Nuovi arrivi della settimana</h2>
  <table style="width:100%;border-collapse:collapse">{tabella}</table>
  <p style="text-align:center;margin:20px 0"><a href="{_h(site)}" style="background:#e879a8;color:#fff;padding:10px 18px;border-radius:20px;text-decoration:none">Tutto il catalogo</a></p>
  <p style="text-align:center;font-size:0.9em">Vuoi vederli appena arrivano? Entra nel
  <a href="{_h(TELEGRAM_URL)}" style="color:#e879a8;font-weight:bold">gruppo Telegram di NerdNostalgia</a>:
  nuovi arrivi in tempo reale, scambi e domande.</p>
  <p style="color:#888;font-size:0.85em">Ricevi questa email perche' hai acconsentito alle comunicazioni promozionali.
  <a href="{_h(link_revoca)}" style="color:#888">Revoca il consenso</a>.</p>
</body></html>"""
    return {"text": testo, "html": html}


def _link_revoca(token: str) -> str:
    from utils.email import _site_url
    return f"{_site_url()}/disiscriviti?t={token}"


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
    for dest in destinatari(db):
        corpo = _corpo(articoli, _link_revoca(dest.token_revoca))
        if send_email(to=dest.email, subject=oggetto, text_body=corpo["text"], html_body=corpo["html"]):
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


# ---------------------------------------------------------------------------
# Iscrizione dal footer, senza account: doppio opt-in. L'email lasciata nel
# riquadro riceve un link di conferma; finche' non lo apre non riceve niente,
# cosi' nessuno puo' iscrivere l'indirizzo di un altro.
# ---------------------------------------------------------------------------

CONFERMA_VALIDA = timedelta(days=7)
# Una seconda richiesta per lo stesso indirizzo entro questo tempo non
# rimanda la conferma: il riquadro non deve diventare un modo per
# bombardare di email qualcuno.
RINVIO_CONFERMA = timedelta(minutes=10)


def iscrivi(db: Session, email: str) -> bool:
    """Registra la richiesta e manda il link di conferma. True se l'email di
    conferma e' partita (al chiamante non serve: risponde sempre uguale)."""
    from utils.email import _h, _site_url, send_email
    email = email.strip().lower()
    cliente = db.query(User).filter(User.email == email).first()
    if cliente is not None and cliente.marketing_consent:
        return False
    iscritto = db.query(NewsletterSubscriber).filter(NewsletterSubscriber.email == email).first()
    if iscritto is not None and iscritto.attivo:
        return False
    adesso = _ora()
    if iscritto is None:
        iscritto = NewsletterSubscriber(email=email, unsubscribe_token=secrets.token_urlsafe(32))
        db.add(iscritto)
    elif iscritto.confirm_sent_at and adesso - iscritto.confirm_sent_at < RINVIO_CONFERMA:
        return False
    iscritto.confirm_token = secrets.token_urlsafe(32)
    iscritto.confirm_sent_at = adesso
    db.commit()
    link = f"{_site_url()}/newsletter/conferma?t={iscritto.confirm_token}"
    testo = ("Ciao!\n\nQualcuno (speriamo tu) ha chiesto di ricevere la newsletter dei nuovi "
             "arrivi di NerdNostalgia: una email a settimana, il venerdi', con gli articoli "
             f"appena pubblicati.\n\nPer confermare apri questo link:\n{link}\n\n"
             "Se non sei stato tu, ignora questa email: senza conferma non ti scriveremo.\n")
    html = f"""<html><body style="font-family:sans-serif;max-width:560px;margin:auto;color:#3d2a5c">
  <h2 style="color:#e879a8">Confermi l'iscrizione?</h2>
  <p>Qualcuno (speriamo tu) ha chiesto di ricevere la newsletter dei nuovi arrivi di
  NerdNostalgia: una email a settimana, il venerdì, con gli articoli appena pubblicati.</p>
  <p style="text-align:center;margin:24px 0"><a href="{_h(link)}" style="background:#e879a8;color:#fff;padding:10px 18px;border-radius:20px;text-decoration:none">Sì, iscrivimi</a></p>
  <p style="color:#888;font-size:0.85em">Se non sei stato tu, ignora questa email: senza conferma non ti scriveremo.</p>
</body></html>"""
    return send_email(to=email, subject="Conferma l'iscrizione alla newsletter di NerdNostalgia",
                      text_body=testo, html_body=html)


def conferma(db: Session, token: str) -> Optional[NewsletterSubscriber]:
    """Il clic sul link di conferma. None se il link non vale (o e' scaduto)."""
    iscritto = (db.query(NewsletterSubscriber)
                .filter(NewsletterSubscriber.confirm_token == token).first()) if token else None
    if iscritto is None:
        return None
    if iscritto.confirm_sent_at and _ora() - iscritto.confirm_sent_at > CONFERMA_VALIDA:
        return None
    iscritto.confirmed_at = _ora()
    iscritto.revoked_at = None
    iscritto.confirm_token = None
    db.commit()
    LOGGER.info("Newsletter: iscrizione confermata (%s)", iscritto.id)
    return iscritto
