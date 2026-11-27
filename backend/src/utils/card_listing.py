"""
Messa in vendita di una carta della collezione su CardTrader e su eBay.

A differenza del carico rapido non si passa da un articolo in bozza: la
carta vive gia' nella collezione (personal_cards), che ha i suoi conti.
Un articolo in piu' la conterebbe due volte nel magazzino.

Il prezzo e' quello scelto sulla carta (list_price); se manca, il
suggerito. Mai un prezzo inventato: senza nessuno dei due ci si ferma.

eBay vuole almeno una foto pubblica: lo scan va benissimo, ed e' meglio
di qualsiasi foto col telefono.
"""
import io
import logging
import re
from datetime import datetime, timezone
from decimal import ROUND_CEILING, Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from models.db import (
    Article, ArticleCondition, ArticleStatus, CardBlueprint, Category, MarketplaceFee, PersonalCard, PersonalCardStatus,
)
from utils import card_names_it as cn
from utils import cardtrader_client as ct
from utils import ebay_client as eb
from utils.card_pricing import NOMI_GIOCO
from utils import storage
from utils.cardtrader_sync import _extract_product_id

LOGGER = logging.getLogger("card_listing")

# Categoria eBay "Carte collezionabili singole" (CCG Individual Cards).
# Sovrascrivibile da impostazioni: l'albero categorie cambia per mercato.
EBAY_CATEGORIA_CARTE = "183454"

# Condizioni CardTrader → descrittore eBay "Card Condition" (40001), che
# nelle carte non gradate (conditionId 4000 = USED_VERY_GOOD) sostituisce
# la condizione generica.
EBAY_CONDIZIONE_CARTA = {
    "Mint": "400010",
    "Near Mint": "400010",          # Near mint or better
    "Slightly Played": "400015",    # Lightly played (Excellent)
    "Moderately Played": "400016",  # Moderately played (Very good)
    "Played": "400017",             # Heavily played (Poor)
    "Poor": "400017",
}

LINGUE_EBAY = {
    "it": "Italiano", "en": "Inglese", "fr": "Francese", "de": "Tedesco",
    "es": "Spagnolo", "pt": "Portoghese", "jp": "Giapponese",
}


def nome_vetrina(card: PersonalCard) -> str:
    """Il nome come e' stampato: italiano per le carte italiane, se lo si
    conosce (vedi riempi_nomi_italiani), se no quello di CardTrader."""
    if (card.language or "").lower() == "it" and card.name_it:
        return card.name_it
    return card.name


def set_vetrina(card: PersonalCard) -> Optional[str]:
    if (card.language or "").lower() == "it" and card.collection_it:
        return card.collection_it
    return card.collection


def riempi_nomi_italiani(db: Session, card: PersonalCard) -> bool:
    """Cerca nome della carta e del set in italiano se mancano. True se ne
    ha trovato almeno uno. Non tocca quelli gia' scritti (anche a mano)."""
    if card.name_it and (card.collection_it or card.game_id != cn.POKEMON):
        return False
    bp = (db.query(CardBlueprint).filter(CardBlueprint.id == card.cardtrader_blueprint_id).first()
          if card.cardtrader_blueprint_id else None)
    nome, nome_set = cn.cerca(card.game_id, card.collection, card.printed_code or card.card_number,
                              codice_set=bp.expansion_code if bp else None,
                              numero=(bp.collector_number if bp else None) or card.card_number,
                              nome_inglese=card.name)
    trovato = False
    if nome and not card.name_it:
        card.name_it, trovato = nome[:200], True
    if nome_set and not card.collection_it:
        card.collection_it, trovato = nome_set[:100], True
    return trovato


def aggiorna_nomi_italiani(db: Session, pausa: float = 0.3) -> Dict[str, int]:
    """Nomi italiani per le carte che non li hanno ancora (confermate prima
    che ci fossero, o con una fonte che allora non rispondeva). Se la carta
    e' in vetrina, l'articolo prende subito titolo e descrizione nuovi: non
    serve ripubblicarla. Le inserzioni eBay/CardTrader no: si aggiornano
    quando le si ripubblica."""
    import time
    carte = (db.query(PersonalCard)
             .filter(PersonalCard.status != PersonalCardStatus.SOLD)
             .filter((PersonalCard.name_it.is_(None)) |
                     ((PersonalCard.game_id == cn.POKEMON) & PersonalCard.collection_it.is_(None)))
             .all())
    trovate = articoli = 0
    for card in carte:
        try:
            if not riempi_nomi_italiani(db, card):
                continue
            trovate += 1
            art = card.article
            if art is not None and art.status == ArticleStatus.PUBLISHED:
                art.title = site_title(card)
                art.description = site_description(card)
                articoli += 1
            db.commit()
        except Exception as exc:  # noqa: BLE001 — una carta non ferma le altre
            db.rollback()
            LOGGER.warning("Nomi italiani per la carta %s: %s", card.id, exc)
        if pausa:
            time.sleep(pausa)
    LOGGER.info("Nomi italiani: %d carte su %d, %d articoli aggiornati", trovate, len(carte), articoli)
    return {"carte": len(carte), "trovate": trovate, "articoli": articoli}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _setting(db: Session, key: str) -> str:
    from helpers.setting import SettingHelper
    return (SettingHelper(db=db).get_value(key) or "").strip()


# Sul sito una carta costa almeno 0,20 €, e sopra i 0,20 almeno 0,50 €:
# sotto, il guadagno se ne va in imballo e tempo. Solo sito: CardTrader,
# eBay e Vinted hanno le loro regole.
SITO_MINIMO = 0.20
SITO_SCALINO = 0.50


def prezzo_sito(prezzo: float) -> float:
    """0,20 → 0,20; 0,11 → 0,20; 0,21-0,49 → 0,50; da 0,50 in su invariato."""
    if prezzo <= SITO_MINIMO:
        return SITO_MINIMO
    if prezzo < SITO_SCALINO:
        return SITO_SCALINO
    return round(prezzo, 2)


def sale_price(card: PersonalCard) -> float:
    prezzo = card.list_price if card.list_price is not None else card.estimated_value
    if prezzo is None or float(prezzo) <= 0:
        raise ValueError("Manca il prezzo: valuta la carta o scrivi il prezzo di vendita")
    return round(float(prezzo), 2)


# Se nella pagina Commissioni non c'e' niente per il marketplace: lo stesso
# ripiego della scheda articolo (useMarketplaceFees.ts), per non pubblicare
# su eBay al prezzo del sito e regalare la commissione.
MARKUP_DI_RIPIEGO = {"ebay": Decimal("11")}


def marketplace_fee(db: Session, marketplace: str, category_id: Optional[int]) -> Tuple[Decimal, Decimal]:
    """Commissione (percentuale, quota fissa) per (marketplace, categoria),
    con la cascata della scheda articolo: categoria → categoria padre →
    default del marketplace → ripiego. Se a un livello ce n'e' piu' d'una si
    prende quella con la percentuale piu' alta: nel dubbio meglio coprire."""
    livelli: List[Optional[int]] = []
    if category_id is not None:
        livelli.append(category_id)
        cat = db.query(Category).filter(Category.id == category_id).first()
        if cat is not None and cat.parent_id:
            livelli.append(cat.parent_id)
    livelli.append(None)
    for livello in livelli:
        q = db.query(MarketplaceFee.markup_percent, MarketplaceFee.fixed_fee)
        q = q.filter(MarketplaceFee.marketplace == marketplace)
        q = q.filter(MarketplaceFee.category_id.is_(None) if livello is None
                     else MarketplaceFee.category_id == livello)
        righe = [(Decimal(str(p)), Decimal(str(f or 0))) for p, f in q.all() if p is not None]
        if righe:
            return max(righe)
    return MARKUP_DI_RIPIEGO.get(marketplace, Decimal("0")), Decimal("0")


def marketplace_markup(db: Session, marketplace: str, category_id: Optional[int]) -> Decimal:
    """Solo la percentuale della commissione (vedi marketplace_fee)."""
    return marketplace_fee(db, marketplace, category_id)[0]


# eBay non accetta inserzioni a prezzo fisso sotto 1 euro (e lo dice solo
# alla pubblicazione, dopo aver creato articolo e offerta).
EBAY_PREZZO_MINIMO = Decimal("1.00")


def ebay_price_auto(db: Session, card: PersonalCard) -> float:
    """Prezzo eBay calcolato: la regola di Vinted (vedi regola_carte)
    applicata al prezzo che copre la commissione eBay.

    Si parte da dove parte Vinted (minimo CardTrader, se no il prezzo della
    carta) e si aggiunge la commissione eBay (percentuale + quota fissa).
    La commissione si calcola sul lordo, quindi non basta aggiungere la
    percentuale: lordo = (base + fisso) / (1 - percentuale). Su quello la
    regola: +2 all'euro sopra, +15% oltre i 15 euro, scalini per le carte
    economiche, ma sotto 1 euro resta 1 (il minimo di eBay) invece della
    soglia di 0,90 di Vinted. Con 6,5% + 0,35 euro un minimo CardTrader di
    3 euro fa 3,59 di lordo, e 6 euro su eBay."""
    base = Decimal(str(base_regola(card)))
    percentuale, fisso = marketplace_fee(db, "ebay", _categoria(db, card))
    lordo = (base + fisso) / (1 - percentuale / 100)
    return max(regola_carte(float(lordo), EBAY_SCALINI), float(EBAY_PREZZO_MINIMO))


def _euro_intero(prezzo: Decimal) -> Decimal:
    """Su eBay i prezzi sono senza centesimi: si arrotonda all'euro sopra."""
    return prezzo.quantize(Decimal("1"), rounding=ROUND_CEILING)


def ebay_price(db: Session, card: PersonalCard) -> float:
    """Il prezzo scritto per eBay se c'e' (all'euro sopra, mai sotto il
    minimo di eBay), se no quello calcolato. Solo eBay: sito e CardTrader
    hanno il loro."""
    if card.list_price_ebay is not None and float(card.list_price_ebay) > 0:
        return float(max(_euro_intero(Decimal(str(card.list_price_ebay))), EBAY_PREZZO_MINIMO))
    return ebay_price_auto(db, card)


def cardtrader_price(card: PersonalCard) -> float:
    """Il prezzo scritto per CardTrader se c'e', se no quello del sito."""
    if card.list_price_cardtrader is not None and float(card.list_price_cardtrader) > 0:
        return round(float(card.list_price_cardtrader), 2)
    return sale_price(card)


def _quantita_libera(card: PersonalCard) -> int:
    return max(int(card.quantity or 1), 1)


# ── CardTrader ────────────────────────────────────────────────────

def publish_cardtrader(db: Session, card: PersonalCard) -> Dict[str, Any]:
    if not card.cardtrader_blueprint_id:
        raise ValueError("Carta non abbinata a CardTrader")
    prezzo = cardtrader_price(card)
    qty = _quantita_libera(card)
    if card.cardtrader_product_id:
        ct.update_product(card.cardtrader_product_id, price=prezzo, quantity=qty)
        azione = "updated"
    else:
        footer = _setting(db, "cardtrader_footer") or None
        resp = ct.create_product(
            blueprint_id=card.cardtrader_blueprint_id,
            price_eur=prezzo,
            quantity=qty,
            condition=card.condition or "Near Mint",
            language=(card.language or "").lower() or None,
            reverse=bool(card.reverse),
            first_edition=bool(card.first_edition),
            description=footer,
        )
        card.cardtrader_product_id = _extract_product_id(resp)
        azione = "created"
    card.cardtrader_synced_at = _now()
    db.commit()
    return {"action": azione, "product_id": card.cardtrader_product_id, "price_eur": prezzo}


def unpublish_cardtrader(db: Session, card: PersonalCard) -> None:
    if not card.cardtrader_product_id:
        return
    try:
        ct.delete_product(card.cardtrader_product_id)
    except ct.CardTraderError as exc:
        if exc.status != 404:  # gia' tolta su CardTrader: va bene cosi'
            raise
    card.cardtrader_product_id = None
    card.cardtrader_synced_at = _now()
    db.commit()


# ── eBay ──────────────────────────────────────────────────────────

def ebay_sku(card: PersonalCard) -> str:
    """Lo SKU in uso (puo' avere un suffisso, vedi _sku_nuovo)."""
    return card.ebay_sku or f"NN-PC-{card.id}"


def _sku_nuovo(card: PersonalCard) -> str:
    """NN-PC-12 → NN-PC-12-r2 → NN-PC-12-r3: uno SKU mai usato, per
    ripartire da un'offerta pulita quando eBay blocca quella vecchia."""
    m = re.search(r"-r(\d+)$", card.ebay_sku or "")
    return f"NN-PC-{card.id}-r{int(m.group(1)) + 1 if m else 2}"


def _offerta_bloccata(exc: "eb.EbayError") -> bool:
    """eBay ha tolto l'inserzione per una violazione delle regole (25098:
    "offerte di acquisto o vendita al di fuori di eBay") e non permette di
    rimettere in vendita quell'offerta, nemmeno dopo averla corretta."""
    body = exc.body if isinstance(exc.body, dict) else {}
    return any(e.get("errorId") == 25098 for e in body.get("errors") or [] if isinstance(e, dict))


def ebay_title(card: PersonalCard) -> str:
    """Massimo 80 caratteri: prima cio' che si cerca (nome, codice),
    poi cio' che rassicura (lingua, condizione)."""
    parti = [nome_vetrina(card)]
    if card.printed_code:
        parti.append(card.printed_code)
    # Subito dopo il codice: reverse e prima edizione cambiano il prezzo,
    # e chi le cerca scrive proprio questo.
    if card.reverse:
        parti.append("Reverse")
    if card.first_edition:
        parti.append("1a Edizione")
    if set_vetrina(card):
        parti.append(set_vetrina(card))
    lingua = LINGUE_EBAY.get((card.language or "").lower())
    if lingua:
        parti.append(lingua.upper()[:3])
    if card.condition:
        parti.append(card.condition)
    titolo = " ".join(p for p in parti if p)
    gioco = NOMI_GIOCO.get(card.game_id or 0)
    if gioco and len(titolo) + len(gioco) + 1 <= 80:
        titolo = f"{gioco} {titolo}"
    return titolo[:80]


# Cosa eBay considera un invito a comprare fuori da eBay: link, domini,
# email, telefoni, social e gli altri canali di vendita. La riga che ne
# contiene uno si scarta intera: l'inserzione verrebbe nascosta.
_FUORI_EBAY = re.compile(
    r"https?://|www\.|\b[\w-]+\.(store|com|it|net|org|eu|shop)\b|@"
    r"|whats\s?app|telegram|instagram|facebook|tiktok"
    r"|vinted|subito|cardtrader|cardmarket|wallapop"
    r"|(?:\+?\d[\s./-]?){9,}",  # telefono: almeno 9 cifre (le date ne hanno 8)
    re.IGNORECASE,
)


def senza_contatti_esterni(testo: str) -> str:
    """Il testo senza le righe che rimandano fuori da eBay."""
    return "\n".join(r for r in testo.splitlines() if not _FUORI_EBAY.search(r)).strip()


def _descrizione(db: Session, card: PersonalCard) -> str:
    righe = [f"<p><b>{ebay_title(card)}</b></p>", "<ul>"]
    for etichetta, valore in (
        ("Espansione", set_vetrina(card)),
        ("Numero", card.printed_code or card.card_number),
        ("Lingua", LINGUE_EBAY.get((card.language or "").lower(), card.language)),
        ("Condizione", card.condition),
        ("Prima edizione", "Sì" if card.first_edition else None),
        ("Reverse / foil", "Sì" if card.reverse else None),
    ):
        if valore:
            righe.append(f"<li>{etichetta}: {valore}</li>")
    righe.append("</ul><p>Nelle foto la carta che riceverai (scansione).</p>")
    footer = senza_contatti_esterni(_setting(db, "marketplace_footer_ebay"))
    if footer:
        righe.append("<p>" + "<br>".join(footer.splitlines()) + "</p>")
    return "".join(righe)


def _ebay_config(db: Session) -> Dict[str, str]:
    conf = {
        "fulfillmentPolicyId": _setting(db, "ebay_fulfillment_policy_id"),
        "paymentPolicyId": _setting(db, "ebay_payment_policy_id"),
        "returnPolicyId": _setting(db, "ebay_return_policy_id"),
        "merchantLocationKey": _setting(db, "ebay_merchant_location_key"),
        "categoryId": _setting(db, "ebay_card_category_id") or EBAY_CATEGORIA_CARTE,
    }
    mancanti = [k for k, v in conf.items() if not v]
    if mancanti:
        raise ValueError(
            "Impostazioni eBay incomplete (Impostazioni → eBay): " + ", ".join(mancanti)
        )
    return conf


def _immagini(card: PersonalCard) -> list:
    """eBay scarica le foto da sé: servono URL pubblici in https."""
    return [u for u in (card.images or []) if isinstance(u, str) and u.startswith("https://")][:12]


def _aspetti(card: PersonalCard) -> Dict[str, List[str]]:
    """Item specifics della carta."""
    aspetti = {"Gioco": [NOMI_GIOCO.get(card.game_id or 0, "Altro")]}
    if card.name:
        aspetti["Nome carta"] = [nome_vetrina(card)]
    if set_vetrina(card):
        aspetti["Set"] = [set_vetrina(card)]
    if card.printed_code or card.card_number:
        aspetti["Numero carta"] = [card.printed_code or card.card_number]
    lingua = LINGUE_EBAY.get((card.language or "").lower())
    if lingua:
        aspetti["Lingua"] = [lingua]
    return aspetti


def _articolo_ebay(db: Session, card: PersonalCard, aspetti: Dict[str, List[str]],
                   foto: list) -> Dict[str, Any]:
    """Inventory item della carta (PUT /inventory_item/{sku})."""
    return {
        "availability": {"shipToLocationAvailability": {"quantity": _quantita_libera(card)}},
        # 4000 "Non gradata" per le carte collezionabili
        "condition": "USED_VERY_GOOD",
        "conditionDescriptors": [{
            "name": "40001",
            "values": [EBAY_CONDIZIONE_CARTA.get(card.condition or "Near Mint", "400010")],
        }],
        "product": {
            "title": ebay_title(card),
            "description": _descrizione(db, card),
            "imageUrls": foto,
            "aspects": aspetti,
        },
    }


def _offerta_ebay(db: Session, card: PersonalCard, conf: Dict[str, str], sku: str,
                  prezzo: float) -> Dict[str, Any]:
    return {
        "sku": sku,
        "marketplaceId": eb.marketplace_id(),
        "format": "FIXED_PRICE",
        "availableQuantity": _quantita_libera(card),
        "categoryId": conf["categoryId"],
        "listingDescription": _descrizione(db, card),
        "listingPolicies": {
            "fulfillmentPolicyId": conf["fulfillmentPolicyId"],
            "paymentPolicyId": conf["paymentPolicyId"],
            "returnPolicyId": conf["returnPolicyId"],
        },
        "merchantLocationKey": conf["merchantLocationKey"],
        "pricingSummary": {"price": {"value": f"{prezzo:.2f}", "currency": "EUR"}},
    }


def publish_ebay(db: Session, card: PersonalCard) -> Dict[str, Any]:
    if not eb.is_configured():
        raise ValueError("eBay non collegato: completa il consenso OAuth da Impostazioni")
    if card.ebay_group_key and card.ebay_listing_id:
        raise ValueError("La carta e' in un'inserzione eBay con varianti: si aggiorna da li'")
    if card.ebay_group_key:
        # Agganciata a un gruppo che eBay non ha mai pubblicato: e' libera.
        from utils import ebay_variations
        ebay_variations.scarta_gruppo_mai_pubblicato(db, card)
    conf = _ebay_config(db)
    prezzo = ebay_price(db, card)
    foto = _immagini(card)
    if not foto:
        raise ValueError("eBay vuole almeno una foto pubblica (https): manca lo scan")
    sku = ebay_sku(card)
    articolo = _articolo_ebay(db, card, _aspetti(card), foto)
    eb.put_inventory_item(sku, articolo)
    offerta = _offerta_ebay(db, card, conf, sku, prezzo)
    offer_id = card.ebay_offer_id
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
    card.ebay_sku = sku
    card.ebay_offer_id = offer_id
    db.commit()

    if not card.ebay_listing_id:
        try:
            pub = eb.publish_offer(offer_id) or {}
        except eb.EbayError as exc:
            if not _offerta_bloccata(exc):
                raise
            # L'offerta vecchia e' marchiata: la si toglie e si riparte da
            # uno SKU nuovo, con descrizione e prezzo di adesso.
            LOGGER.warning("Offerta eBay %s bloccata da eBay (25098): ne creo una nuova", offer_id)
            try:
                eb.delete_offer(offer_id)
            except eb.EbayError as exc_del:
                LOGGER.info("Offerta %s non cancellata: %s", offer_id, exc_del)
            sku = _sku_nuovo(card)
            eb.put_inventory_item(sku, articolo)
            offer_id = (eb.create_offer({**offerta, "sku": sku}) or {}).get("offerId")
            card.ebay_sku, card.ebay_offer_id = sku, offer_id
            db.commit()
            try:
                pub = eb.publish_offer(offer_id) or {}
            except eb.EbayError as exc2:
                if _offerta_bloccata(exc2):
                    raise ValueError(
                        "eBay blocca anche l'offerta nuova per 'vendita fuori da eBay': c'e' ancora un "
                        "link, un'email o un altro canale nella descrizione (Impostazioni → footer eBay)"
                    ) from exc2
                raise
            azione = "recreated"
        card.ebay_listing_id = pub.get("listingId")
    card.ebay_synced_at = _now()
    db.commit()
    return {"action": azione, "listing_id": card.ebay_listing_id, "price_eur": prezzo,
            "url": ebay_listing_url(card)}


def ebay_listing_url(card: PersonalCard) -> Optional[str]:
    if not card.ebay_listing_id:
        return None
    host = "sandbox.ebay.com" if eb.is_sandbox() else "www.ebay.it"
    return f"https://{host}/itm/{card.ebay_listing_id}"


def unpublish_ebay(db: Session, card: PersonalCard) -> None:
    if card.ebay_group_key:
        # Voce di un'inserzione con varianti: si toglie la voce, le altre restano.
        from utils import ebay_variations
        ebay_variations.remove_card(db, card)
        return
    if card.ebay_offer_id and card.ebay_listing_id:
        try:
            eb.withdraw_offer(card.ebay_offer_id)
        except eb.EbayError as exc:
            if exc.status != 404:
                raise
    card.ebay_listing_id = None
    card.ebay_synced_at = _now()
    db.commit()


# ── Sito (vetrina) ────────────────────────────────────────────────
#
# Sul sito si vende tramite un articolo: e' li' che passano carrello e
# ordini. La carta ne ha uno solo, che si ripubblica invece di duplicarlo.
# Le foto sono quelle dello scan, COPIATE nell'articolo: cancellare la
# carta o lo scan non deve lasciare l'articolo senza immagini.

# game_id CardTrader → sottocategoria di "Carte" sul sito
CATEGORIA_GIOCO = {5: "pokemon", 1: "magic-the-gathering", 4: "yu-gi-oh", 15: "one-piece"}

CONDIZIONI_IT = {
    "Mint": "Mint", "Near Mint": "Near Mint (come nuova)",
    "Slightly Played": "Slightly Played (lievi segni d'uso)",
    "Moderately Played": "Moderately Played (segni d'uso evidenti)",
    "Played": "Played (molto giocata)", "Poor": "Poor (danneggiata)",
}


def _categoria(db: Session, card: PersonalCard) -> Optional[int]:
    slug = CATEGORIA_GIOCO.get(card.game_id or 0)
    for s in ([slug] if slug else []) + ["carte"]:
        cat = db.query(Category).filter(Category.slug == s).first()
        if cat:
            return cat.id
    return None


# Come si scrivono in vetrina (NOMI_GIOCO resta senza accenti: e' il valore
# dell'item specific "Gioco" su eBay).
GIOCHI_VETRINA = {5: "Pokémon", 1: "Magic", 4: "Yu-Gi-Oh!", 15: "One Piece"}


# Le sigle di CardTrader: chi compra carte le riconosce al volo.
SIGLE_CONDIZIONE = {
    "Mint": "M", "Near Mint": "NM", "Slightly Played": "SP",
    "Moderately Played": "MP", "Played": "PL", "Poor": "PO",
}


def site_title(card: PersonalCard) -> str:
    """Es. "Pokémon · Durant ex · Surging Sparks 004/191 (IT, NM)": il gioco
    in testa, che nel catalogo del sito si cerca anche per quello."""
    gioco = GIOCHI_VETRINA.get(card.game_id or 0)
    parti = ([gioco, "·"] if gioco else []) + [
        nome_vetrina(card), "·", set_vetrina(card) or "", card.printed_code or card.card_number or ""]
    lingua = (card.language or "").upper()
    condizione = SIGLE_CONDIZIONE.get(card.condition or "", "")
    extra = [x for x in (lingua, condizione, "1ª ed." if card.first_edition else "",
                         "Reverse" if card.reverse else "") if x]
    titolo = " ".join(p for p in parti if p)
    if extra:
        titolo += f" ({', '.join(extra)})"
    return titolo[:255]


def _numero_breve(card: PersonalCard) -> Optional[str]:
    """"061/100" → "61": come lo scrive chi cerca. I codici con lettere
    ("TG05/TG30", "LOB-IT005") restano come sono, senza il totale."""
    codice = (card.printed_code or card.card_number or "").split("/")[0].strip()
    if codice.isdigit():
        return codice.lstrip("0") or "0"
    return codice or None


def vinted_title(card: PersonalCard) -> str:
    """Es. "Spearow 61 ex guardiani dei cristalli IT pokemon": nome, numero
    corto, set in minuscolo, lingua, gioco. Le parole che si scrivono nella
    ricerca di Vinted, senza la punteggiatura del titolo del sito."""
    parti = [nome_vetrina(card), _numero_breve(card)]
    if card.reverse:
        parti.append("reverse")
    if card.first_edition:
        parti.append("1a edizione")
    parti += [(set_vetrina(card) or "").lower(), (card.language or "").upper(),
              NOMI_GIOCO.get(card.game_id or 0, "").lower()]
    return " ".join(p for p in parti if p)


VINTED_SOGLIA = 15.0
VINTED_RICARICO = 2.0
# Sopra la soglia il ricarico cresce: su Vinted si tratta (offerte di solito
# 10-20% sotto), e sulle carte care 2-3 euro non lasciano margine.
VINTED_QUOTA_SOPRA = 0.15
# Carte economiche, a scalini di un euro: sotto 0,90 → 1; 0,90-1,10 → 2;
# fino a 1,90 → 3. Da li' la regola +2 (1,95 → 4), senza salti.
VINTED_SCALINI = ((0.90, 1.0), (1.10, 2.0), (1.90, 3.0))
# eBay, sul prezzo con le commissioni: sotto 1 euro resta 1 (il minimo di
# eBay), poi gli stessi scalini di Vinted.
EBAY_SCALINI = ((1.00, 1.0), (1.10, 2.0), (1.90, 3.0))


def base_regola(card: PersonalCard) -> float:
    """Da dove parte la regola: il minimo CardTrader, se no il prezzo della
    carta (ValueError se non c'e' nemmeno quello)."""
    if card.cardtrader_price is not None and float(card.cardtrader_price) > 0:
        return float(card.cardtrader_price)
    return sale_price(card)


def regola_carte(base: float, scalini) -> float:
    """La regola che usi su Vinted: base + 2 euro arrotondato all'euro
    superiore, cioe' da +2 a +3 (2,60 → 5; 12,10 → 15). Sopra i 15 euro in
    piu' il 15% della parte che supera i 15, cosi' il ricarico cresce col
    prezzo senza salti (20 → 23, 30 → 35, 50 → 58, 100 → 115). Le carte
    economiche a scalini (vedi VINTED_SCALINI, EBAY_SCALINI)."""
    import math
    for i, (fino_a, prezzo) in enumerate(scalini):
        # Il primo scalino esclude il suo limite (0,90 e' gia' "intorno all'euro").
        if base < fino_a or (i > 0 and base <= fino_a):
            return prezzo
    extra = max(base - VINTED_SOGLIA, 0) * VINTED_QUOTA_SOPRA
    return float(math.ceil(round(base + VINTED_RICARICO + extra, 6)))


def vinted_price(card: PersonalCard) -> Optional[float]:
    """Prezzo per Vinted: la regola (regola_carte) sul minimo CardTrader, o
    sul prezzo della carta se il minimo non c'e'."""
    try:
        base = base_regola(card)
    except ValueError:
        return None
    return regola_carte(base, VINTED_SCALINI)


def vinted_description(card: PersonalCard) -> str:
    """Titolo e lingua; il footer Vinted lo aggiunge chi copia (impostazioni)."""
    lingua = LINGUE_EBAY.get((card.language or "").lower(), card.language or "")
    righe = [vinted_title(card)]
    if lingua:
        righe.append(f"Lingua {lingua.lower()}")
    return "\n".join(righe)


def site_description(card: PersonalCard) -> str:
    righe = [
        f"{nome_vetrina(card)} — {set_vetrina(card) or ''} {card.printed_code or card.card_number or ''}".strip(),
        "",
        f"Lingua: {LINGUE_EBAY.get((card.language or '').lower(), card.language or '—')}",
        f"Condizione: {CONDIZIONI_IT.get(card.condition or '', card.condition or '—')}",
    ]
    if card.first_edition:
        righe.append("Prima edizione")
    if card.reverse:
        righe.append("Reverse / foil")
    righe += ["", "Le foto sono la scansione della carta che riceverai."]
    return "\n".join(righe)


def _copia_foto(card: PersonalCard, article: Article) -> list:
    """Copia gli scan nella cartella dell'articolo (nuove varianti WebP)."""
    urls = []
    for u in card.images or []:
        path = storage.path_from_internal_url(u)
        if not path or not path.exists():
            continue
        with open(path, "rb") as fh:
            url, _ = storage.save_upload("articles", article.id, io.BytesIO(fh.read()), "image/webp")
        urls.append(url)
    return urls


def publish_site(db: Session, card: PersonalCard, admin_id: int) -> Dict[str, Any]:
    """Mette la carta in vetrina. Se l'articolo c'e' gia' lo riallinea
    (prezzo, quantita', testi) e lo ripubblica."""
    prezzo = prezzo_sito(sale_price(card))
    if card.status == PersonalCardStatus.SOLD:
        raise ValueError("La carta risulta gia' venduta")
    article = card.article
    nuovo = article is None
    if nuovo:
        article = Article(user_id=admin_id, title=site_title(card), price=prezzo, images=[])
        db.add(article)
        db.flush()  # serve l'id per la cartella delle foto
    elif article.status == ArticleStatus.SOLD:
        raise ValueError("L'articolo sul sito risulta gia' venduto")

    article.title = site_title(card)
    article.description = site_description(card)
    article.price = prezzo
    article.quantity = _quantita_libera(card)
    article.condition = ArticleCondition.USED
    article.category_id = _categoria(db, card)
    article.card_collection = (card.collection or "")[:100] or None
    article.card_number = card.printed_code or card.card_number
    article.card_condition = card.condition
    article.card_language = (card.language or "")[:5] or None
    article.card_reverse = bool(card.reverse)
    article.card_first_edition = bool(card.first_edition)
    article.cost = card.purchase_cost
    if nuovo or not article.images:
        article.images = _copia_foto(card, article)
    if not article.images:
        db.rollback()
        raise ValueError("Mancano le foto: lo scan della carta non e' piu' disponibile")
    era_pubblicato = article.status == ArticleStatus.PUBLISHED
    article.mark_as_published()
    card.article_id = article.id
    db.commit()

    if not era_pubblicato:
        # Come una pubblicazione normale: avvisi a chi segue la categoria.
        # Niente auto-push CardTrader: la carta ha la sua inserzione.
        try:
            from utils.category_alerts import notify_new_article
            notify_new_article(db, article)
        except Exception as exc:  # noqa: BLE001
            LOGGER.info("Avvisi categoria non inviati per articolo %s: %s", article.id, exc)
    return {"action": "created" if nuovo else "updated", "article_id": article.id, "price_eur": prezzo}


def unpublish_site(db: Session, card: PersonalCard) -> None:
    """Toglie la carta dalla vetrina. L'articolo si archivia, non si
    cancella: puo' essere legato a ordini, e lo si ripubblica uguale."""
    article = card.article
    if article is not None and article.status == ArticleStatus.PUBLISHED:
        article.status = ArticleStatus.ARCHIVED
        db.commit()


def on_article_sold(db: Session, article: Article, piattaforma: str = "sito") -> None:
    """Venduta sul sito: la carta della collezione diventa VENDUTA e si
    ritira da CardTrader ed eBay, per non venderla due volte. Best effort:
    la vendita sul sito non deve fallire per un marketplace che non
    risponde (l'errore finisce nei log, l'inserzione va ritirata a mano)."""
    card = db.query(PersonalCard).filter(PersonalCard.article_id == article.id).first()
    if card is None or card.status == PersonalCardStatus.SOLD:
        return
    card.status = PersonalCardStatus.SOLD
    card.sold_date = _now().date()
    card.sold_platform = piattaforma
    card.sale_price = article.vinted_price if piattaforma == "vinted" and article.vinted_price else article.price
    db.commit()
    for nome, fn, attiva in (("CardTrader", unpublish_cardtrader, card.cardtrader_product_id),
                             ("eBay", unpublish_ebay, card.ebay_listing_id)):
        if not attiva:
            continue
        try:
            fn(db, card)
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            LOGGER.warning("Carta %s venduta sul sito ma non ritirata da %s: %s", card.id, nome, exc)


def is_collection_article(db: Session, article: Article) -> bool:
    if not getattr(article, "id", None):
        return False
    try:
        return db.query(PersonalCard.id).filter(PersonalCard.article_id == article.id).first() is not None
    except Exception:  # noqa: BLE001 — nel dubbio non si blocca niente
        return False


# ── Correzione di una carta in collezione ─────────────────────────
#
# Lo scanner a volte conferma la carta sbagliata (versione, numero) o con
# condizione e lingua sbagliate. Si corregge dalla collezione, e dove la
# carta e' gia' in vendita l'inserzione si riallinea.

# Cosa cambia la carta in vendita: su CardTrader non si modifica, si ritira
# e si ripubblica.
CAMBI_DI_CARTA = {"carta", "condition", "language", "reverse", "first_edition"}


def correggi_carta(db: Session, card: PersonalCard, *, blueprint_id: Optional[int] = None,
                   condition: Optional[str] = None, language: Optional[str] = None,
                   reverse: Optional[bool] = None, first_edition: Optional[bool] = None,
                   quantity: Optional[int] = None) -> set:
    """Applica la correzione e ritorna cosa e' cambiato. Cambiando carta
    nome, set e numero vengono dal blueprint, e i prezzi di mercato (che
    erano della carta sbagliata) si rifanno."""
    cambiati = set()
    if blueprint_id and blueprint_id != card.cardtrader_blueprint_id:
        bp = db.query(CardBlueprint).filter(CardBlueprint.id == blueprint_id).first()
        if bp is None:
            raise ValueError(f"Carta {blueprint_id} non trovata nell'indice")
        card.name = bp.name
        card.collection = bp.expansion_name
        card.card_number = bp.collector_number
        card.printed_code = bp.collector_number
        card.game_id = bp.game_id
        card.cardtrader_blueprint_id = bp.id
        card.cardtrader_expansion_id = bp.expansion_id
        card.name_it = None
        card.collection_it = None
        cambiati.add("carta")
    for campo, valore in (("condition", condition), ("language", (language or "").lower() or None),
                          ("reverse", reverse), ("first_edition", first_edition), ("quantity", quantity)):
        if valore is not None and getattr(card, campo) != valore:
            setattr(card, campo, valore)
            cambiati.add(campo)
    db.commit()
    if "carta" in cambiati:
        from utils import card_pricing as cp
        try:
            cp.price_card(card)
            riempi_nomi_italiani(db, card)
            db.commit()
        except Exception as exc:  # noqa: BLE001 — la correzione resta, il prezzo si rifa' a mano
            db.rollback()
            LOGGER.warning("Prezzi o nomi della carta %s dopo la correzione: %s", card.id, exc)
    return cambiati


def riallinea_canali(db: Session, card: PersonalCard, cambiati: set, admin_id: int,
                     voci_prima=None) -> Dict[str, str]:
    """Riporta la correzione dove la carta e' in vendita. Ogni canale va per
    conto suo: ritorna gli errori per canale, da mostrare."""
    from utils import ebay_variations
    avvisi: Dict[str, str] = {}
    if not cambiati:
        return avvisi

    def prova(canale, fn):
        try:
            fn()
        except (ValueError, ct.CardTraderError, eb.EbayError) as exc:
            db.rollback()
            avvisi[canale] = str(exc)

    if card.cardtrader_product_id:
        def cardtrader():
            if cambiati & CAMBI_DI_CARTA:
                unpublish_cardtrader(db, card)
            publish_cardtrader(db, card)
        prova("cardtrader", cardtrader)
    if card.ebay_listing_id:
        if card.ebay_group_key and voci_prima is not None:
            prova("ebay", lambda: ebay_variations.aggiorna_voce(db, card, voci_prima))
        elif not card.ebay_group_key:
            prova("ebay", lambda: publish_ebay(db, card))
    if card.article is not None and card.article.status == ArticleStatus.PUBLISHED:
        prova("sito", lambda: publish_site(db, card, admin_id))
    return avvisi
