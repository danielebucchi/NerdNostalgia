"""
Vendite su CardTrader ed eBay → carta venduta e ritirata dagli altri canali.

La vendita sul sito ritira gia' la carta da CardTrader ed eBay
(card_listing.on_article_sold). Al contrario no: una carta venduta su eBay
restava in vendita sul sito e su CardTrader, e poteva vendersi due volte.
Questo controllo, ogni 15 minuti, lo chiude:

  - CardTrader: gli ordini recenti; ogni voce porta il product_id, lo
    stesso salvato sulla carta;
  - eBay: l'offerta di ogni carta in vendita dice quante copie ha venduto
    (listing.soldQuantity). Basta lo scope sell.inventory del consenso che
    c'e' gia': niente Fulfillment API, niente nuovo consenso.

Una carta da piu' copie diventa venduta quando le copie vendute arrivano
alla quantita'. Ogni errore resta nel suo canale: CardTrader che non
risponde non ferma il controllo su eBay.

Lo stesso per gli articoli del sito messi su eBay o CardTrader dalla loro
scheda (non carte della collezione): venduto fuori, l'articolo diventa
venduto e si ritira dagli altri canali. Vinted non ha API: se l'articolo
c'era, l'email dice di toglierlo a mano.
"""
import logging
from datetime import date, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from models.db import Article, ArticleStatus, PersonalCard, PersonalCardStatus
from models.db.articles import EbayStatus, VintedStatus
from utils import card_listing as cl
from utils import cardtrader_client as ct
from utils import ebay_client as eb

LOGGER = logging.getLogger("sales_sync")

GIORNI_ORDINI = 30
PAGINE_MAX = 10
STATI_ANNULLATI = {"canceled", "cancelled", "request_for_cancel"}


def _in_vendita(db: Session) -> List[PersonalCard]:
    return (db.query(PersonalCard)
            .filter(PersonalCard.status != PersonalCardStatus.SOLD)
            .all())


def segna_venduta(db: Session, card: PersonalCard, piattaforma: str,
                  prezzo: Optional[float]) -> List[str]:
    """La carta e' venduta su `piattaforma`: diventa VENDUTA e si ritira
    dagli altri canali. Ritorna i canali da cui NON si e' riusciti a
    ritirarla (da fare a mano)."""
    card.status = PersonalCardStatus.SOLD
    card.sold_date = date.today()
    card.sold_platform = piattaforma
    if prezzo is not None:
        card.sale_price = prezzo
    db.commit()
    rimasti = []
    altri = [
        ("sito", cl.unpublish_site, card.article is not None),
        ("cardtrader", cl.unpublish_cardtrader, bool(card.cardtrader_product_id)),
        ("ebay", cl.unpublish_ebay, bool(card.ebay_listing_id)),
    ]
    for nome, fn, attivo in altri:
        if not attivo or nome == piattaforma:
            continue
        try:
            fn(db, card)
        except Exception as exc:  # noqa: BLE001 — un canale non ferma gli altri
            db.rollback()
            LOGGER.warning("Carta %s venduta su %s ma non ritirata da %s: %s", card.id, piattaforma, nome, exc)
            rimasti.append(nome)
    return rimasti


def _ordini_cardtrader() -> List[dict]:
    dal = (date.today() - timedelta(days=GIORNI_ORDINI)).isoformat()
    ordini: List[dict] = []
    for pagina in range(1, PAGINE_MAX + 1):
        blocco = ct._request("GET", "/orders", params={"page": pagina, "limit": 50, "from": dal})
        if not isinstance(blocco, list) or not blocco:
            break
        ordini.extend(blocco)
        if len(blocco) < 50:
            break
    return ordini


def _vendute_cardtrader(db: Session, carte: List[PersonalCard]) -> Dict[int, dict]:
    """card.id → {quantita, prezzo} venduti su CardTrader."""
    per_prodotto = {c.cardtrader_product_id: c for c in carte if c.cardtrader_product_id}
    if not per_prodotto:
        return {}
    vendute: Dict[int, dict] = {}
    for ordine in _ordini_cardtrader():
        if (ordine.get("state") or "").lower() in STATI_ANNULLATI:
            continue
        for voce in ordine.get("order_items") or []:
            card = per_prodotto.get(voce.get("product_id"))
            if card is None or voce.get("deleted_at"):
                continue
            v = vendute.setdefault(card.id, {"quantita": 0, "prezzo": None})
            v["quantita"] += int(voce.get("quantity") or 1)
            cents = ct._price_to_cents(voce.get("seller_price"))
            if cents is not None:
                v["prezzo"] = cents / 100
    return vendute


def _vendute_ebay(carte: List[PersonalCard]) -> Dict[int, dict]:
    vendute: Dict[int, dict] = {}
    for card in carte:
        if not card.ebay_listing_id or not card.ebay_sku:
            continue
        offerte = (eb.get_offers(card.ebay_sku) or {}).get("offers") or []
        for offerta in offerte:
            venduti = int(((offerta.get("listing") or {}).get("soldQuantity")) or 0)
            if venduti:
                prezzo = ((offerta.get("pricingSummary") or {}).get("price") or {}).get("value")
                vendute[card.id] = {"quantita": venduti, "prezzo": float(prezzo) if prezzo else None}
    return vendute


# ── Articoli del sito su eBay / CardTrader ───────────────────────

def _articoli_in_vendita(db: Session) -> List[Article]:
    carte = {r[0] for r in db.query(PersonalCard.article_id).filter(PersonalCard.article_id.isnot(None))}
    return [a for a in (db.query(Article)
                        .filter(Article.status != ArticleStatus.SOLD)
                        .filter((Article.ebay_listing_id.isnot(None)) | (Article.cardtrader_product_id.isnot(None)))
                        .all())
            if a.id not in carte]


def _articoli_venduti_cardtrader(articoli: List[Article]) -> Dict[int, dict]:
    per_prodotto = {a.cardtrader_product_id: a for a in articoli if a.cardtrader_product_id}
    if not per_prodotto:
        return {}
    vendute: Dict[int, dict] = {}
    for ordine in _ordini_cardtrader():
        if (ordine.get("state") or "").lower() in STATI_ANNULLATI:
            continue
        for voce in ordine.get("order_items") or []:
            art = per_prodotto.get(voce.get("product_id"))
            if art is None or voce.get("deleted_at"):
                continue
            v = vendute.setdefault(art.id, {"quantita": 0, "prezzo": None})
            v["quantita"] += int(voce.get("quantity") or 1)
            cents = ct._price_to_cents(voce.get("seller_price"))
            if cents is not None:
                v["prezzo"] = cents / 100
    return vendute


def _articoli_venduti_ebay(articoli: List[Article]) -> Dict[int, dict]:
    vendute: Dict[int, dict] = {}
    for art in articoli:
        if not art.ebay_listing_id or not art.ebay_sku:
            continue
        for offerta in (eb.get_offers(art.ebay_sku) or {}).get("offers") or []:
            venduti = int(((offerta.get("listing") or {}).get("soldQuantity")) or 0)
            if venduti:
                prezzo = ((offerta.get("pricingSummary") or {}).get("price") or {}).get("value")
                vendute[art.id] = {"quantita": venduti, "prezzo": float(prezzo) if prezzo else None}
    return vendute


def segna_articolo_venduto(db: Session, article: Article, piattaforma: str) -> List[str]:
    """L'articolo e' venduto su `piattaforma`: venduto anche sul sito, e via
    dagli altri canali. Ritorna i canali da sistemare a mano."""
    from datetime import datetime, timezone
    from utils import article_ebay
    from utils import cardtrader_sync as cts
    adesso = datetime.now(timezone.utc).replace(tzinfo=None)
    article.status = ArticleStatus.SOLD
    article.sold_at = article.sold_at or adesso
    if piattaforma == "ebay":
        article.ebay_status = EbayStatus.SOLD
    db.commit()
    rimasti = []
    altri = [
        ("cardtrader", lambda: cts.unpublish_article(db, article), bool(article.cardtrader_product_id)),
        ("ebay", lambda: article_ebay.unpublish(db, article), bool(article.ebay_listing_id)),
    ]
    for nome, fn, attivo in altri:
        if not attivo or nome == piattaforma:
            continue
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 — un canale non ferma gli altri
            db.rollback()
            LOGGER.warning("Articolo %s venduto su %s ma non ritirato da %s: %s", article.id, piattaforma, nome, exc)
            rimasti.append(nome)
    if article.vinted_status == VintedStatus.LISTED:
        rimasti.append("vinted")  # niente API: va tolto a mano
    return rimasti


def _controlla_articoli(db: Session, esito: Dict[str, object]) -> None:
    articoli = _articoli_in_vendita(db)
    if not articoli:
        return
    fonti = []
    if ct.is_configured():
        fonti.append(("cardtrader", lambda: _articoli_venduti_cardtrader(articoli)))
    if eb.is_configured():
        fonti.append(("ebay", lambda: _articoli_venduti_ebay(articoli)))
    per_id = {a.id: a for a in articoli}
    for piattaforma, leggi in fonti:
        try:
            vendute = leggi()
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Controllo vendite articoli %s fallito: %s %s", piattaforma, exc, getattr(exc, "body", ""))
            esito["errori"][f"{piattaforma} (articoli)"] = str(exc)
            continue
        for art_id, v in vendute.items():
            art = per_id.get(art_id)
            if art is None or art.status == ArticleStatus.SOLD:
                continue
            if v["quantita"] < (art.quantity or 1) - (art.quantity_sold or 0):
                continue  # ne restano pezzi: resta in vendita
            rimasti = segna_articolo_venduto(db, art, piattaforma)
            esito["vendute"].append({"article_id": art.id, "nome": art.title, "piattaforma": piattaforma,
                                     "prezzo": v["prezzo"], "da_ritirare_a_mano": rimasti})


def run(db: Session) -> Dict[str, object]:
    """Un giro di controllo. Ritorna cosa ha trovato, per i log e l'email."""
    carte = _in_vendita(db)
    esito: Dict[str, object] = {"vendute": [], "errori": {}}
    fonti = []
    if ct.is_configured():
        fonti.append(("cardtrader", lambda: _vendute_cardtrader(db, carte)))
    if eb.is_configured():
        fonti.append(("ebay", lambda: _vendute_ebay(carte)))
    per_id = {c.id: c for c in carte}
    for piattaforma, leggi in fonti:
        try:
            vendute = leggi()
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Controllo vendite %s fallito: %s %s", piattaforma, exc, getattr(exc, "body", ""))
            esito["errori"][piattaforma] = str(exc)
            continue
        for card_id, v in vendute.items():
            card = per_id.get(card_id)
            if card is None or card.status == PersonalCardStatus.SOLD:
                continue
            if v["quantita"] < int(card.quantity or 1):
                continue  # ne restano copie: resta in vendita
            rimasti = segna_venduta(db, card, piattaforma, v["prezzo"])
            esito["vendute"].append({"card_id": card.id, "nome": cl.nome_vetrina(card),
                                     "piattaforma": piattaforma, "prezzo": v["prezzo"],
                                     "da_ritirare_a_mano": rimasti})
    _controlla_articoli(db, esito)
    if esito["vendute"]:
        _avvisa(esito["vendute"])
    return esito


def _avvisa(vendute: List[dict]) -> None:
    from utils.email import _config, send_email
    righe = []
    for v in vendute:
        prezzo = f" a {v['prezzo']:.2f} €" if v["prezzo"] is not None else ""
        riga = f"- {v['nome']}: venduto su {v['piattaforma']}{prezzo}, ritirato dagli altri canali"
        if v["da_ritirare_a_mano"]:
            riga += f" TRANNE {', '.join(v['da_ritirare_a_mano'])}: da togliere a mano"
        righe.append(riga)
    send_email(
        to=_config()["to_admin"],
        subject=f"Vendute fuori dal sito: {len(vendute)}",
        text_body="Vendite trovate su CardTrader / eBay:\n\n" + "\n".join(righe),
    )
