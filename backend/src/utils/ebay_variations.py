"""
Piu' carte in un'unica inserzione eBay con varianti ("scegli la carta").

Ogni carta resta un articolo eBay a se' (SKU, offerta, prezzo, quantita' e
foto propri, come nella pubblicazione singola), ma non si pubblica da sola:
le carte stanno in un inventory item group che dice a eBay che variano per
"Carta", e si pubblica il gruppo. Ne esce una pagina con il menu a tendina:
meno inserzioni da pagare e da tenere d'occhio per tante carte da pochi euro.

Il gruppo vive su eBay; qui ogni carta ricorda solo la chiave del gruppo
(ebay_group_key) e condivide l'ebay_listing_id con le altre. Aggiungere
carte a un gruppo esistente lo riscrive con tutte le voci e lo ripubblica:
l'inserzione resta la stessa.
"""
import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from models.db import PersonalCard
from utils import card_listing as cl
from utils import ebay_client as eb

LOGGER = logging.getLogger("ebay_variations")

# La caratteristica per cui variano le voci: il nome del menu sulla pagina.
ASPETTO_VARIANTE = "Carta"
# Limiti eBay: 250 varianti per inserzione, 65 caratteri per valore.
MAX_VARIANTI = 250
MAX_VALORE = 65
MAX_TITOLO = 80


def etichetta(card: PersonalCard) -> str:
    """Voce del menu: cosa distingue questa carta dalle altre a colpo
    d'occhio (nome, numero, condizione)."""
    parti = [cl.nome_vetrina(card), card.printed_code or card.card_number, card.condition]
    return " ".join(p for p in parti if p)[:MAX_VALORE].strip()


def _chiave_numero(card: PersonalCard):
    """"004/102" → 4, "TG05/TG30" → 5: il numero stampato come lo si conta.
    Prima l'espansione, poi il numero, poi l'id (stabile fra due copie)."""
    codice = (card.printed_code or card.card_number or "").split("/")[0]
    cifre = re.search(r"\d+", codice)
    lettere = re.sub(r"[\d\s]", "", codice)  # "TG" di "TG05": "004" e "4" sono lo stesso numero
    return (card.collection or "", int(cifre.group()) if cifre else 10**9, lettere, card.id)


def ordina_per_numero(carte: List[PersonalCard]) -> List[PersonalCard]:
    """Le voci del menu nell'ordine del raccoglitore: per espansione e
    numero. Lo stesso ordine ovunque si riscrive il gruppo: il suffisso
    "#id" dei doppioni dipende da chi viene prima."""
    return sorted(carte, key=_chiave_numero)


def _etichette_uniche(carte: List[PersonalCard]) -> Dict[int, str]:
    """Due copie della stessa carta nella stessa condizione avrebbero la
    stessa voce, che eBay rifiuta: la seconda prende l'id."""
    viste: Dict[str, int] = {}
    esito: Dict[int, str] = {}
    for c in carte:
        base = etichetta(c) or f"Carta {c.id}"
        valore = base
        if valore in viste:
            suffisso = f" #{c.id}"
            valore = base[:MAX_VALORE - len(suffisso)] + suffisso
        viste[valore] = c.id
        esito[c.id] = valore
    return esito


def _aspetti_comuni(carte: List[PersonalCard]) -> Dict[str, List[str]]:
    """Gli item specifics uguali per tutte le carte (es. Gioco, Lingua): a
    livello di gruppo. Quelli diversi da carta a carta eBay li accetta solo
    se sono la caratteristica per cui variano, quindi restano fuori."""
    aspetti = [cl._aspetti(c) for c in carte]
    comuni = dict(aspetti[0])
    for a in aspetti[1:]:
        comuni = {k: v for k, v in comuni.items() if a.get(k) == v}
    return comuni


def _descrizione_gruppo(db: Session, titolo: str) -> str:
    righe = [
        f"<p><b>{titolo}</b></p>",
        "<p>Scegli la carta dal menu: ogni voce ha il suo prezzo e la sua condizione. "
        "Nelle foto della voce la carta che riceverai (scansione).</p>",
    ]
    footer = cl.senza_contatti_esterni(cl._setting(db, "marketplace_footer_ebay"))
    if footer:
        righe.append("<p>" + "<br>".join(footer.splitlines()) + "</p>")
    return "".join(righe)


def scarta_gruppo_mai_pubblicato(db: Session, card: PersonalCard) -> None:
    """La carta e' agganciata a un gruppo che eBay non ha mai pubblicato
    (tentativo rifiutato): il gruppo si cancella anche su eBay, dove tiene
    occupati gli SKU, e la carta torna libera."""
    chiave = card.ebay_group_key
    if not chiave or card.ebay_listing_id:
        return
    try:
        eb.delete_inventory_item_group(chiave)
    except eb.EbayError as exc:
        if exc.status != 404:
            LOGGER.info("Gruppo eBay %s non cancellato: %s", chiave, exc)
    for c in db.query(PersonalCard).filter(PersonalCard.ebay_group_key == chiave).all():
        if not c.ebay_listing_id:
            c.ebay_group_key = None
    db.commit()


def _salva_offerta(card: PersonalCard, sku: str, offerta: Dict[str, Any]) -> str:
    """Crea o aggiorna l'offerta della voce, senza pubblicarla: nel gruppo
    si pubblica tutto insieme."""
    offer_id = card.ebay_offer_id
    if not offer_id:
        try:
            esistenti = (eb.get_offers(sku) or {}).get("offers") or []
            offer_id = esistenti[0]["offerId"] if esistenti else None
        except eb.EbayError as exc:
            if exc.status != 404:
                raise
    if offer_id:
        eb.update_offer(offer_id, offerta)
        return offer_id
    return (eb.create_offer(offerta) or {}).get("offerId")


def _scrivi_gruppo(db: Session, chiave: str, titolo: str, carte: List[PersonalCard]) -> Dict[str, Any]:
    """Articoli, offerte e gruppo su eBay per queste carte, poi pubblica."""
    conf = cl._ebay_config(db)
    voci = _etichette_uniche(carte)
    comuni = _aspetti_comuni(carte)
    foto_gruppo: List[str] = []
    for c in carte:
        foto = cl._immagini(c)
        sku = cl.ebay_sku(c)
        aspetti = {**comuni, ASPETTO_VARIANTE: [voci[c.id]]}
        eb.put_inventory_item(sku, cl._articolo_ebay(db, c, aspetti, foto))
        c.ebay_offer_id = _salva_offerta(c, sku, cl._offerta_ebay(db, c, conf, sku, cl.ebay_price(db, c)))
        c.ebay_sku = sku
        c.ebay_group_key = chiave
        if foto and len(foto_gruppo) < 12:
            foto_gruppo.append(foto[0])
    db.commit()

    try:
        _pubblica_gruppo(db, chiave, titolo, carte, voci, comuni, foto_gruppo)
    except eb.EbayError as exc:
        # La risposta di eBay e' gia' nei log (EbayError la scrive sempre):
        # qui solo quale gruppo.
        LOGGER.warning("eBay rifiuta l'inserzione con varianti %s", chiave)
        if not any(c.ebay_listing_id for c in carte):
            # Mai pubblicata: le carte tornano libere, se no restano agganciate
            # a un gruppo che non esiste e non si vendono piu' nemmeno da sole.
            scarta_gruppo_mai_pubblicato(db, carte[0])
        raise
    url = cl.ebay_listing_url(carte[0])
    return {"group_key": chiave, "listing_id": carte[0].ebay_listing_id, "url": url, "count": len(carte)}


def _pubblica_gruppo(db: Session, chiave: str, titolo: str, carte: List[PersonalCard],
                     voci: Dict[int, str], comuni: Dict[str, List[str]], foto_gruppo: List[str]) -> None:
    eb.put_inventory_item_group(chiave, {
        "title": titolo,
        "description": _descrizione_gruppo(db, titolo),
        "imageUrls": foto_gruppo,
        "aspects": comuni,
        "variantSKUs": [cl.ebay_sku(c) for c in carte],
        "variesBy": {
            # La foto cambia con la voce scelta: il compratore vede la sua carta.
            "aspectsImageVariesBy": [ASPETTO_VARIANTE],
            "specifications": [{"name": ASPETTO_VARIANTE, "values": [voci[c.id] for c in carte]}],
        },
    })
    pub = eb.publish_by_inventory_item_group(chiave) or {}
    listing_id = pub.get("listingId")
    adesso = cl._now()
    for c in carte:
        c.ebay_listing_id = listing_id
        c.ebay_synced_at = adesso
    db.commit()


def _titolo_attuale(chiave: str) -> Optional[str]:
    try:
        return (eb.get_inventory_item_group(chiave) or {}).get("title")
    except eb.EbayError as exc:
        if exc.status == 404:
            return None
        raise


def publish_group(db: Session, carte: List[PersonalCard], titolo: Optional[str] = None,
                  chiave: Optional[str] = None) -> Dict[str, Any]:
    """Le carte in un'unica inserzione con varianti. Con `chiave` si
    aggiungono a un gruppo esistente (le voci che ha gia' restano)."""
    if not eb.is_configured():
        raise ValueError("eBay non collegato: completa il collegamento dalla pagina eBay del pannello")
    titolo = (titolo or "").strip()

    gia_dentro: List[PersonalCard] = []
    if chiave:
        gia_dentro = db.query(PersonalCard).filter(PersonalCard.ebay_group_key == chiave).all()
        if not gia_dentro:
            raise ValueError(f"Inserzione con varianti {chiave} non trovata")
        titolo = titolo or _titolo_attuale(chiave) or ""
    if not titolo:
        raise ValueError("Serve un titolo per l'inserzione (es. 'Carte Pokemon singole - scegli la tua')")
    if len(titolo) > MAX_TITOLO:
        raise ValueError(f"Titolo troppo lungo: eBay ne accetta {MAX_TITOLO} caratteri")

    for c in carte:
        # Resto di un tentativo che eBay ha rifiutato: la carta e' libera.
        scarta_gruppo_mai_pubblicato(db, c)
    problemi = []
    for c in carte:
        if c.status == "SOLD":
            problemi.append(f"{c.name}: venduta")
        elif c.ebay_group_key and c.ebay_group_key != chiave:
            problemi.append(f"{c.name}: e' gia' in un'altra inserzione con varianti")
        elif c.ebay_listing_id and not c.ebay_group_key:
            problemi.append(f"{c.name}: e' gia' su eBay da sola, toglila prima da eBay")
        elif not cl._immagini(c):
            problemi.append(f"{c.name}: manca lo scan (eBay vuole una foto)")
        else:
            try:
                cl.ebay_price(db, c)
            except ValueError:
                problemi.append(f"{c.name}: manca il prezzo")
    if problemi:
        raise ValueError("Non posso metterle insieme: " + "; ".join(problemi))

    tutte = ordina_per_numero(gia_dentro + [c for c in carte if c.id not in {g.id for g in gia_dentro}])
    if len(tutte) < 2:
        raise ValueError("Un'inserzione con varianti vuole almeno 2 carte")
    if len(tutte) > MAX_VARIANTI:
        raise ValueError(f"eBay accetta al massimo {MAX_VARIANTI} carte per inserzione")
    return _scrivi_gruppo(db, chiave or f"NN-GRP-{uuid.uuid4().hex[:10]}", titolo, tutte)


def _in_gruppo(db: Session, chiave: str) -> List[PersonalCard]:
    return ordina_per_numero(db.query(PersonalCard)
                             .filter(PersonalCard.ebay_group_key == chiave, PersonalCard.status != "SOLD")
                             .all())


def stato_voci(db: Session, card: PersonalCard) -> Optional[Tuple[Dict[int, str], Dict[str, List[str]]]]:
    """Voci del menu e aspetti comuni del gruppo della carta, com'erano
    prima di correggerla: servono ad aggiorna_voce per capire cosa cambia."""
    if not (card.ebay_group_key and card.ebay_listing_id):
        return None
    carte = _in_gruppo(db, card.ebay_group_key)
    return _etichette_uniche(carte), _aspetti_comuni(carte)


def aggiorna_voce(db: Session, card: PersonalCard,
                  prima: Tuple[Dict[int, str], Dict[str, List[str]]]) -> None:
    """La carta del gruppo e' stata corretta (carta, condizione, lingua...):
    si riscrive la sua voce e si ripubblica il gruppo. Le altre si
    riscrivono solo se cambia la loro voce o gli aspetti comuni a tutte."""
    chiave = card.ebay_group_key
    titolo = _titolo_attuale(chiave)
    if not titolo:
        raise ValueError(f"Inserzione con varianti {chiave} non trovata su eBay")
    voci_prima, comuni_prima = prima
    carte = _in_gruppo(db, chiave)
    voci = _etichette_uniche(carte)
    comuni = _aspetti_comuni(carte)
    conf = cl._ebay_config(db)
    for c in carte:
        if c.id != card.id and comuni == comuni_prima and voci[c.id] == voci_prima.get(c.id):
            continue
        sku = cl.ebay_sku(c)
        eb.put_inventory_item(sku, cl._articolo_ebay(db, c, {**comuni, ASPETTO_VARIANTE: [voci[c.id]]},
                                                     cl._immagini(c)))
        if c.id == card.id:
            c.ebay_offer_id = _salva_offerta(c, sku, cl._offerta_ebay(db, c, conf, sku, cl.ebay_price(db, c)))
    db.commit()
    foto_gruppo = [f[0] for f in (cl._immagini(c) for c in carte) if f][:12]
    _pubblica_gruppo(db, chiave, titolo, carte, voci, comuni, foto_gruppo)


def _togli_voce(db: Session, chiave: str, card: PersonalCard, restano: List[PersonalCard]) -> None:
    """Toglie una voce dal gruppo pubblicato senza riscrivere le altre: si
    aggiorna l'elenco delle varianti e si ripubblica. Riscrivere ogni carta
    (decine di chiamate) bastava che eBay ne sbagliasse una per non poter
    piu' togliere niente. Si riscrive solo una carta la cui voce cambia
    (il suffisso "#id" dei doppioni dipende da chi c'e')."""
    titolo = _titolo_attuale(chiave)
    if not titolo:
        raise ValueError(f"Inserzione con varianti {chiave} non trovata su eBay")
    prima = _etichette_uniche(ordina_per_numero(restano + [card]))
    voci = _etichette_uniche(restano)
    comuni = _aspetti_comuni(restano)
    for c in restano:
        if voci[c.id] != prima[c.id]:
            aspetti = {**comuni, ASPETTO_VARIANTE: [voci[c.id]]}
            eb.put_inventory_item(cl.ebay_sku(c), cl._articolo_ebay(db, c, aspetti, cl._immagini(c)))
    foto_gruppo = [f[0] for f in (cl._immagini(c) for c in restano) if f][:12]
    _pubblica_gruppo(db, chiave, titolo, restano, voci, comuni, foto_gruppo)
    # La voce tolta non serve piu' su eBay: via articolo (e la sua offerta).
    try:
        eb.delete_inventory_item(cl.ebay_sku(card))
    except eb.EbayError as exc:
        LOGGER.info("Articolo eBay %s non cancellato: %s", cl.ebay_sku(card), exc)


def remove_card(db: Session, card: PersonalCard) -> None:
    """Toglie la carta dall'inserzione con varianti (venduta altrove,
    ritirata). Le altre restano in vendita; se ne resta una sola il gruppo
    non ha piu' senso e l'inserzione si chiude."""
    chiave = card.ebay_group_key
    altre = ordina_per_numero(db.query(PersonalCard)
                              .filter(PersonalCard.ebay_group_key == chiave, PersonalCard.id != card.id)
                              .all())
    restano = [c for c in altre if c.status != "SOLD"]
    if len(restano) >= 2:
        _togli_voce(db, chiave, card, restano)
    else:
        try:
            eb.withdraw_by_inventory_item_group(chiave)
        except eb.EbayError as exc:
            if exc.status != 404:
                raise
        for c in restano:
            c.ebay_listing_id = None
            c.ebay_group_key = None
            c.ebay_synced_at = cl._now()
    if card.ebay_offer_id:
        try:
            eb.delete_offer(card.ebay_offer_id)
        except eb.EbayError as exc:
            LOGGER.info("Offerta %s non cancellata: %s", card.ebay_offer_id, exc)
    card.ebay_offer_id = None
    card.ebay_listing_id = None
    card.ebay_group_key = None
    card.ebay_synced_at = cl._now()
    db.commit()
