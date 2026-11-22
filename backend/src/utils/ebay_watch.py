"""
Inserzioni eBay sparite: un controllo ogni ora, e un'email se eBay ne ha
chiusa o nascosta una che non risulta venduta.

eBay puo' togliere un'inserzione ore dopo averla pubblicata (es. "offerte
di acquisto o vendita al di fuori di eBay") senza che l'app lo sappia: la
carta o l'articolo risultano in vendita e non lo sono. Qui si guarda lo
stato dell'offerta (listing.listingStatus) di ogni inserzione dell'app:
carte singole, inserzioni con varianti (una voce basta), articoli. Per
quelle non piu' attive si chiede a eBay il motivo (Trading GetItem) e si
manda un'email. Ognuna si segnala una volta sola: l'elenco delle gia'
segnalate sta nelle impostazioni (chiave interna), e ne esce quando torna
attiva o non e' piu' in vendita.

Le vendite le gestisce sales_sync: un'inserzione chiusa perche' venduta
tutta non si segnala.
"""
import json
import logging
import re
from typing import Dict, List, Optional

import requests
from sqlalchemy.orm import Session

from models.db import Article, ArticleStatus, PersonalCard, PersonalCardStatus
from utils import article_ebay
from utils import card_listing as cl
from utils import ebay_client as eb

LOGGER = logging.getLogger("ebay_watch")

CHIAVE_AVVISATE = "_ebay_watch_avvisate"
TRADING_URL = "https://api.ebay.com/ws/api.dll"


def _inserzioni(db: Session) -> Dict[str, dict]:
    """listing_id → {nome, sku, quantita, url} delle inserzioni dell'app in vendita."""
    trovate: Dict[str, dict] = {}
    carte = (db.query(PersonalCard)
             .filter(PersonalCard.ebay_listing_id.isnot(None), PersonalCard.status != PersonalCardStatus.SOLD)
             .all())
    for c in carte:
        if c.ebay_listing_id in trovate:
            continue  # inserzione con varianti: basta una voce
        nome = f"inserzione con varianti {c.ebay_group_key}" if c.ebay_group_key else cl.nome_vetrina(c)
        trovate[c.ebay_listing_id] = {"nome": nome, "sku": cl.ebay_sku(c), "quantita": int(c.quantity or 1),
                                      "url": cl.ebay_listing_url(c)}
    articoli = (db.query(Article)
                .filter(Article.ebay_listing_id.isnot(None), Article.status != ArticleStatus.SOLD)
                .all())
    for a in articoli:
        trovate.setdefault(a.ebay_listing_id, {
            "nome": a.title, "sku": article_ebay.ebay_sku(a),
            "quantita": (a.quantity or 1) - (a.quantity_sold or 0), "url": article_ebay.listing_url(a)})
    return trovate


def _stato(sku: str) -> Optional[dict]:
    """Stato dell'offerta: {status, venduti}, None se eBay non la trova."""
    offerte = (eb.get_offers(sku) or {}).get("offers") or []
    if not offerte:
        return None
    listing = offerte[0].get("listing") or {}
    return {"status": (listing.get("listingStatus") or "").upper(),
            "venduti": int(listing.get("soldQuantity") or 0)}


def _motivo(listing_id: str) -> Optional[str]:
    """Il messaggio di eBay sull'inserzione (Trading GetItem), se c'e'."""
    xml = ('<?xml version="1.0" encoding="utf-8"?><GetItemRequest xmlns="urn:ebay:apis:eBLBaseComponents">'
           f"<ItemID>{listing_id}</ItemID></GetItemRequest>")
    try:
        r = requests.post(TRADING_URL, data=xml.encode(), timeout=60, headers={
            "X-EBAY-API-IAF-TOKEN": eb._access_token(), "X-EBAY-API-CALL-NAME": "GetItem",
            "X-EBAY-API-SITEID": "101", "X-EBAY-API-COMPATIBILITY-LEVEL": "1349",
            "Content-Type": "text/xml"})
        r.encoding = "utf-8"
        m = re.search(r"<LongMessage>(.*?)</LongMessage>", r.text, re.S) \
            or re.search(r"<ShortMessage>(.*?)</ShortMessage>", r.text, re.S)
        return m.group(1).strip() if m else None
    except Exception as exc:  # noqa: BLE001 — il motivo e' un di piu'
        LOGGER.info("Motivo dell'inserzione %s non letto: %s", listing_id, exc)
        return None


def _gia_avvisate(db: Session) -> List[str]:
    try:
        return list(json.loads(cl._setting(db, CHIAVE_AVVISATE) or "[]"))
    except ValueError:
        return []


def _salva_avvisate(db: Session, ids: List[str]) -> None:
    from helpers.setting import SettingHelper
    SettingHelper(db=db).upsert(CHIAVE_AVVISATE, json.dumps(sorted(set(ids))))
    db.commit()


def run(db: Session) -> Dict[str, object]:
    """Un giro di controllo. Ritorna le inserzioni sparite trovate."""
    esito: Dict[str, object] = {"sparite": [], "errori": 0}
    if not eb.is_configured():
        return esito
    inserzioni = _inserzioni(db)
    avvisate = set(_gia_avvisate(db))
    ancora = set()
    for listing_id, info in inserzioni.items():
        try:
            stato = _stato(info["sku"])
        except eb.EbayError as exc:
            LOGGER.info("Stato dell'inserzione %s non letto: %s", listing_id, exc)
            esito["errori"] += 1
            continue
        if stato and stato["status"] == "ACTIVE":
            continue
        if stato and stato["venduti"] >= info["quantita"]:
            continue  # venduta tutta: la vendita la gestisce sales_sync
        ancora.add(listing_id)
        if listing_id in avvisate:
            continue
        esito["sparite"].append({**info, "listing_id": listing_id,
                                 "status": (stato or {}).get("status") or "offerta non trovata",
                                 "motivo": _motivo(listing_id)})
    if esito["sparite"]:
        _avvisa(esito["sparite"])
    # Restano in elenco solo quelle ancora sparite: se una torna attiva e
    # sparisce di nuovo, si segnala di nuovo.
    nuove = ancora
    if nuove != avvisate:
        _salva_avvisate(db, list(nuove))
    return esito


def _avvisa(sparite: List[dict]) -> None:
    from utils.email import _config, send_email
    righe = []
    for s in sparite:
        riga = f"- {s['nome']}: {s['status']}"
        if s.get("url"):
            riga += f"\n  {s['url']}"
        if s.get("motivo"):
            riga += f"\n  eBay dice: {s['motivo']}"
        righe.append(riga)
    send_email(
        to=_config()["to_admin"],
        subject=f"eBay: {len(sparite)} inserzion{'e' if len(sparite) == 1 else 'i'} non piu' attiv{'a' if len(sparite) == 1 else 'e'}",
        text_body=(
            "Queste inserzioni dell'app su eBay non sono piu' attive, ma la carta o l'articolo "
            "risultano ancora in vendita:\n\n" + "\n\n".join(righe) +
            "\n\nCosa fare: controlla i messaggi di eBay nel Seller Hub. Se eBay l'ha tolta per una "
            "regola (es. vendita fuori da eBay), correggi titolo o descrizione e ripubblica dall'app "
            "(Aggiorna su eBay / Pubblica): un'offerta bloccata si sostituisce con una nuova."
        ),
    )
