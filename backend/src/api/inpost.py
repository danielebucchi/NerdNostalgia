"""
API InPost: configurazione del Geowidget (la mappa dei locker).

Il Geowidget e' la mappa ufficiale InPost (Leaflet + OpenStreetMap, nessuna
chiave Google Maps da pagare). Il token e' PUBBLICO ma legato al dominio: ne
serve uno per localhost e uno per il dominio di produzione.

Lo serviamo da qui invece che da una NEXT_PUBLIC_*: cambiarlo o passare da
test a produzione non richiede di ricostruire il frontend.

NB: NIENTE `from __future__ import annotations` (vedi api/orders.py).
"""
import os

from fastapi import APIRouter

router = APIRouter(prefix="/api/inpost", tags=["inpost"])

# Host del widget. Configurabile perche' InPost pubblica il Geowidget su host
# diversi per mercato: se per l'Italia cambia, si sposta da env senza toccare
# il codice.
DEFAULT_WIDGET_BASE = "https://geowidget.inpost.pl"


def _token() -> str:
    return (os.getenv("INPOST_GEOWIDGET_TOKEN") or "").strip()


def is_configured() -> bool:
    return bool(_token())


@router.get("/config")
def config():
    """Dati per montare la mappa nel browser."""
    base = (os.getenv("INPOST_WIDGET_BASE") or DEFAULT_WIDGET_BASE).rstrip("/")
    return {
        "configured": is_configured(),
        "token": _token(),
        "script_url": f"{base}/inpost-geowidget.js",
        "style_url": f"{base}/inpost-geowidget.css",
        # parcelCollect = punti dove si RITIRA un pacco (quello che ci serve)
        "widget_config": (os.getenv("INPOST_WIDGET_CONFIG") or "parcelCollect").strip(),
        # ATTENZIONE: il Geowidget supporta pl / en / uk. Passando "it" NON
        # ripiega sull'inglese ma sul POLACCO (verificato: i messaggi
        # d'errore escono in polacco). Finche' InPost non aggiunge
        # l'italiano, l'inglese e' il male minore per un cliente italiano.
        "language": (os.getenv("INPOST_WIDGET_LANGUAGE") or "en").strip(),
    }
