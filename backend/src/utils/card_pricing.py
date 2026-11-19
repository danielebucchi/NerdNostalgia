"""
Valutazione di una carta della collezione: CardTrader + venduti eBay.

Due numeri che dicono cose diverse:
- CardTrader e' il prezzo a cui la carta si TROVA in vendita adesso, fra
  inserzioni con la stessa condizione e lingua (il N-esimo piu' basso,
  come nel carico rapido);
- eBay e' il prezzo a cui la carta si e' VENDUTA davvero: la media delle
  ultime dieci vendite concluse.

Il suggerito sta in mezzo: la media dei due. Se ce n'e' uno solo, quello.

Dai venduti eBay si tolgono le inserzioni che non sono la carta sciolta —
gradate (PSA/BGS/CGC), lotti, proxy — perche' un PSA 10 nella media fa
sembrare d'oro una carta da due euro.
"""
import logging
import math
import re
import statistics
import urllib.parse
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, Iterable, List, Optional

from models.db import PersonalCard
from utils import cardtrader_client as ct
from utils import ebay_client as eb

LOGGER = logging.getLogger("card_pricing")

ULTIME_VENDITE = 10
# Il riferimento e' il minimo CardTrader fra le offerte comparabili: il
# suggerito ci aggiunge poco (vedi ricarico). Prima era il secondo piu'
# basso mediato con i venduti eBay, che lo tiravano su: Scambio con minimo
# 2,60 usciva a 7,14.
POSIZIONE_CARDTRADER = 1

# Titoli che non sono "la carta sciolta" e falsano la media.
RE_ESCLUSI = re.compile(
    r"\b(psa|bgs|cgc|beckett|ace\s?\d|graded|gradat[ao]|slab|lott[oi]|lot|bundle|"
    r"set\s+completo|playset|proxy|custom|fan\s?made|replica|orica|"
    r"x\s?\d{1,2}\b|\d{1,2}\s?x)\b",
    re.I,
)

NOMI_GIOCO = {1: "Magic", 4: "Yu-Gi-Oh", 5: "Pokemon", 15: "One Piece"}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _eur(x: Optional[float]) -> Optional[Decimal]:
    if x is None:
        return None
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ── CardTrader ────────────────────────────────────────────────────

def cardtrader_price(card: PersonalCard, position: int = POSIZIONE_CARDTRADER) -> Optional[dict]:
    """Prezzo CardTrader fra le inserzioni comparabili. Se con la lingua
    della carta non c'e' nessuno in vendita, si allarga a tutte le lingue
    (e lo si dice: `same_language` False)."""
    if not card.cardtrader_blueprint_id:
        return None
    comuni = dict(
        condition=card.condition or "Near Mint",
        reverse=bool(card.reverse),
        first_edition=bool(card.first_edition),
    )
    lingua = (card.language or "").lower() or None
    sug = ct.suggested_price_cents(card.cardtrader_blueprint_id, position, language=lingua, **comuni)
    stessa_lingua = True
    if not sug and lingua:
        sug = ct.suggested_price_cents(card.cardtrader_blueprint_id, position, **comuni)
        stessa_lingua = False
    if not sug:
        return None
    return {"eur": round(sug["cents"] / 100, 2), "offers": sug["total"],
            "position": sug["position"], "same_language": stessa_lingua}


# ── eBay ──────────────────────────────────────────────────────────

def ebay_query(card: PersonalCard) -> str:
    """La ricerca come la farebbe un compratore: nome + codice stampato.
    Il codice ("025/165", "LOB-EN001") e' cio' che separa la carta dalle
    sue ristampe; senza, si ripiega sul nome dell'espansione."""
    parti = [card.name]
    if card.printed_code:
        parti.append(card.printed_code)
    elif card.card_number:
        parti.append(card.card_number)
        if card.collection:
            parti.append(card.collection)
    return " ".join(p for p in parti if p).strip()


def ebay_sold_url(card: PersonalCard) -> str:
    """Ricerca dei venduti su ebay.it, da aprire nel browser."""
    q = urllib.parse.quote_plus(ebay_query(card))
    # LH_PrefLoc=1: solo oggetti che si trovano in Italia, come la ricerca via API.
    return f"https://www.ebay.it/sch/i.html?_nkw={q}&LH_Sold=1&LH_Complete=1&_sop=13&LH_PrefLoc=1"


def summarize_sold(vendite: Iterable[dict], n: int = ULTIME_VENDITE) -> Optional[dict]:
    """Ultime `n` vendite valide → media e mediana. Ogni vendita:
    {title, price (euro), date (iso), url}."""
    valide = [
        v for v in vendite
        if v.get("price") and v["price"] > 0 and not RE_ESCLUSI.search(v.get("title") or "")
    ]
    valide.sort(key=lambda v: v.get("date") or "", reverse=True)
    ultime = valide[:n]
    if not ultime:
        return None
    prezzi = [v["price"] for v in ultime]
    return {
        "avg": round(statistics.fmean(prezzi), 2),
        "median": round(statistics.median(prezzi), 2),
        "count": len(ultime),
        "sales": ultime,
    }


def ebay_sold_from_api(card: PersonalCard) -> Optional[dict]:
    grezze = eb.sold_items_search(ebay_query(card))
    vendite = []
    for it in grezze:
        prezzo = it.get("lastSoldPrice") or {}
        if (prezzo.get("currency") or "EUR") != "EUR":
            continue
        try:
            valore = float(prezzo.get("value"))
        except (TypeError, ValueError):
            continue
        vendite.append({
            "title": it.get("title"),
            "price": valore,
            "date": it.get("lastSoldDate"),
            "url": it.get("itemWebUrl"),
        })
    return summarize_sold(vendite)


RE_PREZZO = re.compile(r"\d+(?:[.,]\d{1,2})?")


def parse_manual_prices(testo: str) -> List[float]:
    """Prezzi incollati a mano: "12,50 9.90 15€ 11" → [12.5, 9.9, 15, 11].
    Le virgole decimali all'italiana valgono quanto i punti."""
    return [float(x.replace(",", ".")) for x in RE_PREZZO.findall(testo or "")]


# ── Insieme ───────────────────────────────────────────────────────

# Ricarico sul minimo CardTrader, decrescente col prezzo: sulle carte da
# pochi euro qualche decina di centesimi, sulle care pochi punti percentuali
# (li' anche il 3% sono euro veri, e piu' su si esce dal mercato).
RICARICHI = (
    (1.0, None, 0.10),    # fino a 1 €: +0,10 € fissi
    (5.0, 0.10, None),    # fino a 5 €: +10%
    (20.0, 0.07, None),   # fino a 20 €: +7%
    (50.0, 0.05, None),   # fino a 50 €: +5%
    (None, 0.03, None),   # oltre: +3%
)


def ricarico(minimo: float) -> float:
    """Il minimo CardTrader piu' il ricarico della sua fascia, arrotondato
    ai 5 centesimi superiori (2,60 → 2,90)."""
    for soglia, percentuale, fisso in RICARICHI:
        if soglia is None or minimo <= soglia:
            prezzo = minimo * (1 + percentuale) if percentuale else minimo + fisso
            break
    centesimi = math.ceil(round(prezzo * 100, 6) / 5) * 5
    return round(centesimi / 100, 2)


def suggested(cardtrader_eur: Optional[float], ebay_avg: Optional[float]) -> Optional[float]:
    """Minimo CardTrader + ricarico. I venduti eBay solo se su CardTrader
    non c'e' nessuna offerta: sono pochi, spesso esteri o gradati, e
    tiravano su il prezzo."""
    if cardtrader_eur:
        return ricarico(cardtrader_eur)
    if ebay_avg:
        return round(ebay_avg, 2)
    return None


def apply_ebay(card: PersonalCard, riepilogo: Optional[dict], fonte: str) -> None:
    if riepilogo:
        card.ebay_sold_avg = _eur(riepilogo["avg"])
        card.ebay_sold_count = riepilogo["count"]
        card.ebay_sold = riepilogo["sales"]
    else:
        card.ebay_sold_avg = None
        card.ebay_sold_count = 0
        card.ebay_sold = []
    card.ebay_sold_source = fonte


def refresh_suggested(card: PersonalCard) -> None:
    precedente = card.estimated_value
    sug = suggested(
        float(card.cardtrader_price) if card.cardtrader_price is not None else None,
        float(card.ebay_sold_avg) if card.ebay_sold_avg is not None else None,
    )
    card.estimated_value = _eur(sug)
    card.estimated_value_updated_at = _now().date()
    card.prices_updated_at = _now()
    # Il prezzo di vendita parte dal suggerito, e lo segue finche' non lo si
    # cambia a mano (cioe' finche' e' uguale al suggerito di prima). Un
    # prezzo scritto da te non si tocca.
    mai_toccato = card.list_price is None or (precedente is not None and card.list_price == precedente)
    if mai_toccato and sug is not None:
        card.list_price = _eur(sug)


def price_card(card: PersonalCard) -> Dict[str, Any]:
    """Aggiorna i prezzi di mercato della carta. Ogni fonte va per conto
    suo: eBay che non risponde non deve togliere il prezzo CardTrader.
    Ritorna gli avvisi da mostrare."""
    avvisi: Dict[str, Any] = {}

    try:
        ctp = cardtrader_price(card)
        card.cardtrader_price = _eur(ctp["eur"]) if ctp else None
        card.cardtrader_offers = ctp["offers"] if ctp else 0
        if ctp and not ctp["same_language"]:
            avvisi["cardtrader"] = "nessuna inserzione nella stessa lingua: prezzo su tutte le lingue"
        elif not ctp:
            avvisi["cardtrader"] = "nessuna inserzione comparabile su CardTrader"
    except ct.CardTraderError as exc:
        avvisi["cardtrader"] = str(exc)

    # I venduti inseriti a mano restano finche' non li si sostituisce:
    # sono il lavoro di una persona, un'API spenta non li cancella.
    if card.ebay_sold_source != "manuale":
        if eb.has_app_credentials():
            try:
                apply_ebay(card, ebay_sold_from_api(card), "api")
            except eb.EbayError as exc:
                avvisi["ebay"] = str(exc)
        else:
            avvisi["ebay"] = "eBay non configurato: inserisci i venduti a mano"

    refresh_suggested(card)
    return avvisi
