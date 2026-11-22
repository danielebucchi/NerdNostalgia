"""
Articoli del sito su eBay tramite Inventory API: un'inserzione per articolo
(niente varianti), con le stesse regole delle carte dello scanner.

- Prezzo: quello scritto per eBay nell'articolo se c'e' (all'euro sopra),
  se no la regola delle carte (card_listing.regola_carte) sul prezzo
  dell'articolo piu' la commissione eBay della sua categoria; mai sotto 1
  euro.
- Testi senza link, email o altri canali (eBay toglie le inserzioni che
  rimandano fuori), piu' il footer eBay delle impostazioni.
- Offerta bloccata da eBay (25098): la si sostituisce con una nuova.
- Venduto altrove o archiviato: l'inserzione eBay si ritira.

La categoria eBay la propone eBay dal titolo (Taxonomy API) e resta
nell'articolo (article_metadata["ebay_category_id"]): ripubblicando non
cambia. Gli item specifics obbligatori si riempiono con quello che si sa
(marca, modello, valori della categoria che compaiono nel titolo).

Le carte della collezione (scanner) hanno la loro pubblicazione eBay, anche
con varianti: i loro articoli non passano da qui.
"""
import html
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from models.db import Article, ArticleCondition, ArticleStatus, PersonalCard
from models.db.articles import EbayStatus
from utils import card_listing as cl
from utils import ebay_client as eb

LOGGER = logging.getLogger("article_ebay")

MAX_TITOLO = 80

# Condizione dell'articolo → condizione eBay (Inventory API).
CONDIZIONI_EBAY = {
    ArticleCondition.NEW: "NEW",
    ArticleCondition.USED: "USED_EXCELLENT",
    ArticleCondition.REFURBISHED: "SELLER_REFURBISHED",
    ArticleCondition.FOR_PARTS: "FOR_PARTS_OR_NOT_WORKING",
}

# Item specifics obbligatori di cui non si sa niente: eBay accetta questi.
SENZA_MARCA = "Senza marca"
NON_APPLICABILE = "Non applicabile"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def carta_della_collezione(db: Session, article: Article) -> bool:
    return db.query(PersonalCard.id).filter(PersonalCard.article_id == article.id).first() is not None


def ebay_price_auto(db: Session, article: Article) -> float:
    """La regola delle carte sul prezzo dell'articolo con la commissione eBay
    della sua categoria (sul lordo)."""
    base = Decimal(str(article.price or 0))
    if base <= 0:
        raise ValueError("L'articolo non ha un prezzo")
    percentuale, fisso = cl.marketplace_fee(db, "ebay", article.category_id)
    lordo = (base + fisso) / (1 - percentuale / 100)
    return max(cl.regola_carte(float(lordo), cl.EBAY_SCALINI), float(cl.EBAY_PREZZO_MINIMO))


def ebay_price(db: Session, article: Article) -> float:
    """Il prezzo scritto per eBay se c'e' (all'euro sopra, mai sotto 1 euro),
    se no quello calcolato."""
    if article.ebay_price is not None and float(article.ebay_price) > 0:
        return float(max(cl._euro_intero(Decimal(str(article.ebay_price))), cl.EBAY_PREZZO_MINIMO))
    return ebay_price_auto(db, article)


def ebay_sku(article: Article) -> str:
    return article.ebay_sku or f"NN-ART-{article.id}"


def _sku_nuovo(article: Article) -> str:
    """NN-ART-12 → NN-ART-12-r2 → NN-ART-12-r3: per ripartire da un'offerta
    pulita quando eBay blocca quella vecchia."""
    sku = article.ebay_sku or ""
    n = int(sku.rsplit("-r", 1)[1]) + 1 if "-r" in sku and sku.rsplit("-r", 1)[1].isdigit() else 2
    return f"NN-ART-{article.id}-r{n}"


def listing_url(article: Article) -> Optional[str]:
    if not article.ebay_listing_id:
        return None
    host = "sandbox.ebay.com" if eb.is_sandbox() else "www.ebay.it"
    return f"https://{host}/itm/{article.ebay_listing_id}"


def _quantita(article: Article) -> int:
    return (article.quantity or 1) - (article.quantity_sold or 0)


def _immagini(article: Article) -> List[str]:
    return [u for u in (article.images or []) if isinstance(u, str) and u.startswith("https://")][:12]


def _titolo(article: Article) -> str:
    return (article.title or "").strip()[:MAX_TITOLO].strip()


def _descrizione(db: Session, article: Article) -> str:
    righe = [f"<p><b>{html.escape(_titolo(article))}</b></p>"]
    testo = cl.senza_contatti_esterni(article.description or "")
    if testo:
        righe.append("<p>" + "<br>".join(html.escape(r) for r in testo.splitlines()) + "</p>")
    footer = cl.senza_contatti_esterni(cl._setting(db, "marketplace_footer_ebay"))
    if footer:
        righe.append("<p>" + "<br>".join(html.escape(r) for r in footer.splitlines()) + "</p>")
    return "".join(righe)


def _categoria_carte(db: Session) -> str:
    return cl._setting(db, "ebay_card_category_id") or cl.EBAY_CATEGORIA_CARTE


def categoria(db: Session, article: Article) -> Tuple[str, Optional[str]]:
    """(id, nome) della categoria eBay. La prima volta la propone eBay dal
    titolo; poi resta quella (anche cambiata a mano nei metadati)."""
    meta = dict(article.article_metadata or {})
    if meta.get("ebay_category_id"):
        return str(meta["ebay_category_id"]), meta.get("ebay_category_name")
    cid, nome = None, None
    try:
        albero = eb.default_category_tree_id()
        proposte = (eb.category_suggestions(albero, _titolo(article)) or {}).get("categorySuggestions") or []
        if proposte:
            cid = proposte[0]["category"]["categoryId"]
            nome = proposte[0]["category"].get("categoryName")
    except eb.EbayError as exc:
        LOGGER.info("Categoria eBay non proposta per l'articolo %s: %s", article.id, exc)
    if not cid:
        cid = cl._setting(db, "ebay_default_category_id")
    if not cid:
        raise ValueError("eBay non propone una categoria per questo titolo e manca la categoria "
                         "predefinita (Impostazioni → eBay)")
    meta["ebay_category_id"], meta["ebay_category_name"] = str(cid), nome
    article.article_metadata = meta  # nuovo dict: SQLAlchemy vede il cambio del JSON
    db.commit()
    return str(cid), nome


def _aspetti(article: Article, categoria_id: str) -> Dict[str, List[str]]:
    """Item specifics: quelli che si sanno, e gli obbligatori della categoria
    (un valore ammesso che compare nel titolo, se no "Non applicabile")."""
    aspetti: Dict[str, List[str]] = {}
    if article.brand:
        aspetti["Marca"] = [article.brand.strip()]
    if article.model:
        aspetti["Modello"] = [article.model.strip()]
    if article.card_collection:
        aspetti["Set"] = [article.card_collection]
    if article.card_number:
        aspetti["Numero carta"] = [article.card_number]
    lingua = cl.LINGUE_EBAY.get((article.card_language or "").lower())
    if lingua:
        aspetti["Lingua"] = [lingua]
    try:
        info = eb.item_aspects_for_category(eb.default_category_tree_id(), categoria_id) or {}
    except eb.EbayError as exc:
        LOGGER.info("Caratteristiche della categoria eBay %s non lette: %s", categoria_id, exc)
        return aspetti
    testo = f"{article.title or ''} {article.description or ''}".lower()
    for a in info.get("aspects") or []:
        vincoli = a.get("aspectConstraint") or {}
        nome = a.get("localizedAspectName")
        if not nome or not vincoli.get("aspectRequired") or nome in aspetti:
            continue
        ammessi = [v.get("localizedValue") for v in a.get("aspectValues") or [] if v.get("localizedValue")]
        nel_titolo = [v for v in ammessi if len(v) >= 3 and v.lower() in testo]
        if nel_titolo:
            aspetti[nome] = [max(nel_titolo, key=len)]
        elif nome.lower() in ("marca", "brand"):
            aspetti[nome] = [SENZA_MARCA]
        elif vincoli.get("aspectMode") == "FREE_TEXT" or NON_APPLICABILE in ammessi:
            aspetti[nome] = [NON_APPLICABILE]
        # Altrimenti resta fuori: eBay dira' quale manca.
    return aspetti


def _articolo_ebay(db: Session, article: Article, categoria_id: str) -> Dict[str, Any]:
    item: Dict[str, Any] = {
        "availability": {"shipToLocationAvailability": {"quantity": _quantita(article)}},
        "product": {
            "title": _titolo(article),
            "description": _descrizione(db, article),
            "imageUrls": _immagini(article),
            "aspects": _aspetti(article, categoria_id),
        },
    }
    if categoria_id == _categoria_carte(db):
        # Carte singole: "Non gradata" con la condizione della carta, come lo scanner.
        item["condition"] = "USED_VERY_GOOD"
        item["conditionDescriptors"] = [{
            "name": "40001",
            "values": [cl.EBAY_CONDIZIONE_CARTA.get(article.card_condition or "Near Mint", "400010")],
        }]
    else:
        item["condition"] = CONDIZIONI_EBAY.get(article.condition, "USED_EXCELLENT")
    return item


def _offerta_ebay(db: Session, article: Article, conf: Dict[str, str], sku: str,
                  categoria_id: str, prezzo: float) -> Dict[str, Any]:
    return {
        "sku": sku,
        "marketplaceId": eb.marketplace_id(),
        "format": "FIXED_PRICE",
        "availableQuantity": _quantita(article),
        "categoryId": categoria_id,
        "listingDescription": _descrizione(db, article),
        "listingPolicies": {
            "fulfillmentPolicyId": conf["fulfillmentPolicyId"],
            "paymentPolicyId": conf["paymentPolicyId"],
            "returnPolicyId": conf["returnPolicyId"],
        },
        "merchantLocationKey": conf["merchantLocationKey"],
        "pricingSummary": {"price": {"value": f"{prezzo:.2f}", "currency": "EUR"}},
    }


def _controlli(db: Session, article: Article) -> None:
    if not eb.is_configured():
        raise ValueError("eBay non collegato: completa il collegamento dalla pagina eBay del pannello")
    if carta_della_collezione(db, article):
        raise ValueError("E' una carta della collezione: si mette su eBay dallo scanner carte (Collezione)")
    if article.status in (ArticleStatus.SOLD, ArticleStatus.ARCHIVED):
        raise ValueError("L'articolo e' venduto o archiviato")
    if article.reserved_order_id is not None:
        raise ValueError("L'articolo e' impegnato in un ordine")
    if _quantita(article) < 1:
        raise ValueError("Nessun pezzo disponibile")
    if not _titolo(article):
        raise ValueError("Manca il titolo")
    if not _immagini(article):
        raise ValueError("eBay vuole almeno una foto")


def anteprima(db: Session, article: Article) -> Dict[str, Any]:
    """Cosa andrebbe su eBay, senza pubblicare: prezzo e categoria."""
    try:
        prezzo: Optional[float] = ebay_price(db, article)
    except ValueError:
        prezzo = None
    meta = article.article_metadata or {}
    return {
        "price_eur": prezzo,
        "price_manual": article.ebay_price is not None and float(article.ebay_price) > 0,
        "category_id": meta.get("ebay_category_id"),
        "category_name": meta.get("ebay_category_name"),
        "listing_id": article.ebay_listing_id,
        "url": listing_url(article),
        "collection_card": carta_della_collezione(db, article),
    }


def publish(db: Session, article: Article) -> Dict[str, Any]:
    """Mette l'articolo su eBay, o aggiorna l'inserzione che ha gia'."""
    _controlli(db, article)
    conf = cl._ebay_config(db)
    categoria_id, categoria_nome = categoria(db, article)
    prezzo = ebay_price(db, article)
    sku = ebay_sku(article)
    item = _articolo_ebay(db, article, categoria_id)
    eb.put_inventory_item(sku, item)
    offerta = _offerta_ebay(db, article, conf, sku, categoria_id, prezzo)
    offer_id = article.ebay_offer_id
    if not offer_id:
        # Un'offerta per lo SKU puo' esistere gia' (tentativo precedente
        # fallito alla pubblicazione): la si riusa invece di duplicarla.
        try:
            esistenti = (eb.get_offers(sku) or {}).get("offers") or []
            offer_id = esistenti[0]["offerId"] if esistenti else None
        except eb.EbayError as exc:
            if exc.status != 404:
                raise
    if offer_id:
        eb.update_offer(offer_id, offerta)
        azione = "updated"
    else:
        offer_id = (eb.create_offer(offerta) or {}).get("offerId")
        azione = "created"
    article.ebay_sku, article.ebay_offer_id = sku, offer_id
    db.commit()

    if not article.ebay_listing_id:
        try:
            pub = eb.publish_offer(offer_id) or {}
        except eb.EbayError as exc:
            if not cl._offerta_bloccata(exc):
                raise
            LOGGER.warning("Offerta eBay %s bloccata da eBay (25098): ne creo una nuova", offer_id)
            try:
                eb.delete_offer(offer_id)
            except eb.EbayError as exc_del:
                LOGGER.info("Offerta %s non cancellata: %s", offer_id, exc_del)
            sku = _sku_nuovo(article)
            eb.put_inventory_item(sku, item)
            offer_id = (eb.create_offer({**offerta, "sku": sku}) or {}).get("offerId")
            article.ebay_sku, article.ebay_offer_id = sku, offer_id
            db.commit()
            try:
                pub = eb.publish_offer(offer_id) or {}
            except eb.EbayError as exc2:
                if cl._offerta_bloccata(exc2):
                    raise ValueError(
                        "eBay blocca anche l'offerta nuova per 'vendita fuori da eBay': c'e' ancora un "
                        "link, un'email o un altro canale nella descrizione o nel footer eBay"
                    ) from exc2
                raise
            azione = "recreated"
        article.ebay_listing_id = pub.get("listingId")
    article.ebay_status = EbayStatus.LISTED
    article.ebay_url = listing_url(article)
    article.ebay_synced_at = _now()
    db.commit()
    return {"action": azione, "listing_id": article.ebay_listing_id, "price_eur": prezzo,
            "url": article.ebay_url, "category_id": categoria_id, "category_name": categoria_nome}


def unpublish(db: Session, article: Article) -> None:
    """Ritira l'inserzione (l'offerta resta, per ripubblicarla uguale)."""
    if article.ebay_offer_id and article.ebay_listing_id:
        try:
            eb.withdraw_offer(article.ebay_offer_id)
        except eb.EbayError as exc:
            if exc.status != 404:
                raise
    article.ebay_listing_id = None
    if article.ebay_status == EbayStatus.LISTED:
        article.ebay_status = EbayStatus.NOT_LISTED
        article.ebay_url = None
    article.ebay_synced_at = _now()
    db.commit()


def on_sold_elsewhere(db: Session, article: Article) -> None:
    """Venduto sul sito o su Vinted, o archiviato: l'inserzione eBay si
    ritira, per non vendere due volte lo stesso pezzo. Best effort."""
    if not article.ebay_listing_id:
        return
    try:
        unpublish(db, article)
        LOGGER.info("Articolo %s ritirato da eBay (venduto altrove)", article.id)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        LOGGER.warning("Articolo %s non ritirato da eBay: %s", article.id, exc)
