"""
Sync articolo → prodotto CardTrader (logica condivisa fra l'endpoint
manuale e l'auto-push alla pubblicazione).

CardTrader accetta solo carte agganciate a un blueprint: l'auto-push
scatta SOLO per articoli di categoria "carte" gia' abbinati.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from models.db import Article
from utils import cardtrader_client as ct

LOGGER = logging.getLogger("cardtrader_sync")

# Slug top-level considerati "carte" (l'auto-push agisce solo su questi)
CARD_TOP_SLUGS = {"carte", "cards"}


def is_card_article(article: Article) -> bool:
    cat = article.category
    if cat is None:
        return False
    top_slug = cat.slug if cat.parent_id is None else (cat.parent.slug if cat.parent else cat.slug)
    return (top_slug or "").lower() in CARD_TOP_SLUGS


# ── Risoluzione automatica blueprint da collezione + numero ────────

# Prezzo proposto per gli articoli: il 2° piu' basso fra le inserzioni con
# le stesse caratteristiche (il 1° e' spesso un'occasione o un errore).
POSIZIONE_PREZZO = 2


def _norm_number(s: Optional[str]) -> str:
    """Normalizza un numero carta per il confronto: prende la parte prima
    di '/', tiene alfanumerici, toglie zeri iniziali. '004/102'→'4',
    'TG12/TG30'→'tg12', '015'→'15'."""
    if not s:
        return ""
    head = str(s).strip().lower().split("/")[0]
    head = re.sub(r"[^0-9a-z]", "", head)
    stripped = head.lstrip("0")
    return stripped or head


def _tokens(s: Optional[str]) -> set:
    return set(re.findall(r"[a-z0-9]+", (s or "").lower()))


# I nomi italiani delle carte speciali, come CardTrader le chiama in inglese.
NOMI_ITALIANI = ((r"\bv[\s\-]*astro\b", "vstar"), (r"\bv[\s\-]*max\b", "vmax"),
                 (r"\bv[\s\-]*union\b", "v-union"))


def in_inglese(testo: str) -> str:
    """"Arceus V astro" → "arceus vstar": cosi' lo trova il catalogo CardTrader."""
    testo = (testo or "").lower()
    for italiano, inglese in NOMI_ITALIANI:
        testo = re.sub(italiano, inglese, testo)
    return testo


def numero_semplice(numero: Optional[str]) -> str:
    """Le ristampe tengono la sigla del set originale: "BRS 123" → "123"."""
    m = re.fullmatch(r"\s*[a-z]+\s+0*(\d+)\s*", str(numero or "").split("/")[0].lower())
    return m.group(1) if m else ""


def cerca_blueprint(blueprint: List[Dict[str, Any]], ricerca: str) -> List[Dict[str, Any]]:
    """La ricerca a mano dentro un'espansione: per numero ("123" trova anche
    "BRS 123") o per nome, parola per parola e con i nomi italiani delle
    carte speciali ("arceus v astro" trova "Arceus VSTAR")."""
    q = in_inglese(ricerca.strip())
    parole = [p for p in re.findall(r"[a-z0-9\-]+", q) if p]

    def numero(b):
        return (b.get("fixed_properties") or {}).get("collector_number") or b.get("collector_number")

    trovati = []
    for b in blueprint:
        nome = str(b.get("name", "")).lower()
        n = numero(b)
        per_numero = bool(n) and any(_norm_number(p) and _norm_number(p) in (_norm_number(n), numero_semplice(n))
                                     for p in parole if p.isdigit() or re.fullmatch(r"[a-z]*\d+", p))
        per_nome = bool(parole) and all(p in nome or p.isdigit() and per_numero for p in parole)
        if q in nome or per_nome or (per_numero and all(p in nome for p in parole if not any(c.isdigit() for c in p))):
            trovati.append(b)
    return trovati


def resolve_blueprints(
    collection: Optional[str],
    number: Optional[str],
    name: Optional[str] = None,
    game_id: Optional[int] = None,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Trova i blueprint candidati da collezione+numero (+nome opz.).
    Ritorna lista ordinata per score: {blueprint, expansion, score,
    number_match}. L'abbinamento espansione da testo libero e' euristico:
    per questo si restituiscono candidati da confermare, non 1 secco."""
    exps = ct.expansions_cached()
    if game_id:
        exps = [e for e in exps if e.get("game_id") == game_id]

    coll_l = (collection or "").strip().lower()
    ctoks = _tokens(collection)

    # Espansioni candidate: match su code esatto, substring o token overlap
    scored_exps = []
    for e in exps:
        code = (e.get("code") or "").lower()
        ename = (e.get("name") or "").lower()
        score = 0
        if coll_l and code == coll_l:
            score += 6
        if coll_l and ename == coll_l:
            score += 8  # nome espansione identico → forte preferenza
        if coll_l and (coll_l in ename or ename in coll_l):
            score += 4
        overlap = len(ctoks & _tokens(e.get("name")))
        score += overlap * 2
        if score > 0:
            scored_exps.append((score, e))
    scored_exps.sort(key=lambda x: -x[0])

    target = _norm_number(number)
    ntoks = _tokens(name)
    cands: List[Dict[str, Any]] = []
    # Limita alle prime espansioni per non scaricare troppi export
    for exp_score, e in scored_exps[:6]:
        for bp in ct.blueprints_cached(e["id"]):
            cn = _norm_number((bp.get("fixed_properties") or {}).get("collector_number"))
            num_match = bool(target) and cn == target
            name_overlap = len(ntoks & _tokens(bp.get("name"))) if ntoks else 0
            if not num_match and name_overlap == 0:
                continue
            score = exp_score + (10 if num_match else 0) + name_overlap * 2
            cands.append({
                "blueprint": bp,
                "expansion": {"id": e["id"], "name": e.get("name"), "code": e.get("code")},
                "score": score,
                "number_match": num_match,
            })
    cands.sort(key=lambda x: -x["score"])
    return cands[:limit]


def resolve_single(
    collection: Optional[str],
    number: Optional[str],
    name: Optional[str] = None,
    game_id: Optional[int] = None,
) -> Optional[int]:
    """Blueprint_id SOLO se il match e' inequivocabile: un unico candidato
    col numero esatto, o il migliore col numero esatto nettamente sopra il
    secondo. Altrimenti None (→ abbinamento manuale)."""
    cands = resolve_blueprints(collection, number, name, game_id, limit=5)
    exact = [c for c in cands if c["number_match"]]
    if len(exact) == 1:
        return exact[0]["blueprint"]["id"]
    if len(exact) >= 2 and exact[0]["score"] >= exact[1]["score"] + 6:
        return exact[0]["blueprint"]["id"]
    return None


def resolve_in_expansion(
    expansion_id: Optional[int],
    number: Optional[str],
    name: Optional[str] = None,
) -> Optional[int]:
    """Blueprint univoco DENTRO un'espansione nota (id CardTrader), dato il
    numero carta. Deterministico: niente euristica sul nome dell'espansione
    (è già stata scelta a mano). Se più blueprint hanno lo stesso numero,
    disambigua col nome carta; altrimenti None (→ abbinamento manuale)."""
    target = _norm_number(number)
    if not expansion_id or not target:
        return None
    bps = ct.blueprints_cached(expansion_id)
    matches = [
        bp for bp in bps
        if _norm_number((bp.get("fixed_properties") or {}).get("collector_number")) == target
    ]
    if len(matches) == 1:
        return matches[0]["id"]
    if len(matches) > 1 and name:
        ntoks = _tokens(name)
        scored = sorted(matches, key=lambda b: -len(ntoks & _tokens(b.get("name"))))
        best = len(ntoks & _tokens(scored[0].get("name")))
        second = len(ntoks & _tokens(scored[1].get("name")))
        if best > 0 and best > second:
            return scored[0]["id"]
    return None


def _default_game_id(db) -> Optional[int]:
    try:
        from helpers.setting import SettingHelper
        v = SettingHelper(db=db).get_value("cardtrader_default_game_id")
        return int(v) if v and v.strip().isdigit() else None
    except Exception:  # noqa: BLE001
        return None


def _default_language(db) -> Optional[str]:
    try:
        from helpers.setting import SettingHelper
        v = SettingHelper(db=db).get_value("cardtrader_default_language")
        return v.strip().lower() if v and v.strip() else None
    except Exception:  # noqa: BLE001
        return None


def _cardtrader_description(db, article: Article) -> Optional[str]:
    """Descrizione per l'inserzione CardTrader: descrizione dell'articolo +
    footer configurabile (es. "Ask For Photos / More product on ..."). Le foto
    non si possono caricare via API, quindi il footer invita a chiederle."""
    desc = (article.description or "").strip()
    footer = ""
    try:
        from helpers.setting import SettingHelper
        footer = (SettingHelper(db=db).get_value("cardtrader_footer") or "").strip()
    except Exception:  # noqa: BLE001
        footer = ""
    parts = [p for p in (desc, footer) if p]
    return "\n\n".join(parts) if parts else None


def _extract_product_id(resp: Any) -> Optional[int]:
    if isinstance(resp, dict):
        if isinstance(resp.get("resource"), dict) and "id" in resp["resource"]:
            return resp["resource"]["id"]
        if "id" in resp:
            return resp["id"]
    if isinstance(resp, list) and resp and isinstance(resp[0], dict):
        return resp[0].get("id")
    return None


def publish_article(
    db,
    article: Article,
    *,
    price_eur: Optional[float] = None,
    price_position: int = POSIZIONE_PREZZO,
    quantity: Optional[int] = None,
    condition: Optional[str] = None,
    language: Optional[str] = None,
    reverse: Optional[bool] = None,
    first_edition: Optional[bool] = None,
) -> Dict[str, Any]:
    """Crea (o aggiorna) il prodotto CardTrader per l'articolo.
    Condizione/lingua/reverse/prima-edizione: se non passati, si leggono
    dall'articolo (col default lingua dalle impostazioni). Il prezzo, se non
    forzato, e' il N-esimo piu' basso fra le inserzioni CON LE STESSE
    caratteristiche. Solleva ValueError (dati) o ct.CardTraderError (API)."""
    if not article.cardtrader_blueprint_id:
        raise ValueError("Articolo non abbinato a un blueprint CardTrader")
    from models.db import PersonalCard
    if db.query(PersonalCard.id).filter(PersonalCard.article_id == article.id).first():
        # Pubblicarla anche da qui farebbe due inserzioni della stessa carta.
        raise ValueError("E' una carta della collezione: su CardTrader si mette dallo scanner carte (Collezione)")

    # Attributi effettivi: argomento esplicito → campo articolo → default
    condition = condition or article.card_condition or "Near Mint"
    language = language or article.card_language or _default_language(db)
    reverse = article.card_reverse if reverse is None else reverse
    first_edition = article.card_first_edition if first_edition is None else first_edition

    meta = None
    if price_eur is None:
        sug = ct.suggested_price_cents(
            article.cardtrader_blueprint_id, price_position,
            condition=condition, language=language,
            reverse=bool(reverse), first_edition=bool(first_edition),
        )
        if not sug:
            raise ValueError(
                "Nessuna inserzione di riferimento per il prezzo "
                "(con questa condizione/lingua)"
            )
        price_eur = round(sug["cents"] / 100, 2)
        meta = sug

    qty = quantity or article.quantity or 1

    if article.cardtrader_product_id:
        ct.update_product(article.cardtrader_product_id, price=price_eur, quantity=qty)
        product_id = article.cardtrader_product_id
        action = "updated"
    else:
        resp = ct.create_product(
            blueprint_id=article.cardtrader_blueprint_id,
            price_eur=price_eur,
            quantity=qty,
            condition=condition,
            language=language,
            reverse=bool(reverse),
            first_edition=bool(first_edition),
            description=_cardtrader_description(db, article),
        )
        product_id = _extract_product_id(resp)
        action = "created"

    article.cardtrader_product_id = product_id
    article.cardtrader_synced_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(article)
    return {
        "action": action,
        "product_id": product_id,
        "price_eur": price_eur,
        "quantity": qty,
        "price_meta": meta,
    }


def unpublish_article(db, article: Article) -> bool:
    """Rimuove il prodotto da CardTrader. Best-effort sul 404 (gia' rimosso)."""
    if not article.cardtrader_product_id:
        return False
    try:
        ct.delete_product(article.cardtrader_product_id)
    except ct.CardTraderError as exc:
        if exc.status != 404:
            raise
    article.cardtrader_product_id = None
    db.commit()
    db.refresh(article)
    return True


def auto_publish_if_card(
    db, article: Article, *, expansion_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Hook alla pubblicazione sul sito: se e' una carta abbinabile, la
    pubblica anche su CardTrader col prezzo 2°. Best-effort: non solleva mai
    (la pubblicazione sul sito non deve fallire per CardTrader).

    Se `expansion_id` e' dato (l'utente ha scelto l'espansione esatta), il
    blueprint si trova in modo DETERMINISTICO (id espansione + numero); solo
    in mancanza si ricade sull'euristica dal testo della collezione.

    Ritorna un esito {status, ...} per dare feedback visibile a chi pubblica:
    published / unmatched / skipped / error."""
    try:
        if not ct.is_configured():
            return {"status": "skipped", "reason": "CardTrader non configurato"}
        if not is_card_article(article):
            return {"status": "skipped", "reason": "non è una carta"}
        # Carta della collezione (scanner): ha gia' la sua inserzione
        # CardTrader, gestita dalla collezione. Un'altra sarebbe un doppione.
        from utils.card_listing import is_collection_article
        if is_collection_article(db, article):
            return {"status": "skipped", "reason": "carta della collezione: inserzione gestita dallo scanner"}
        if not article.cardtrader_blueprint_id:
            bp = None
            if expansion_id:
                bp = resolve_in_expansion(expansion_id, article.card_number, article.title)
            if not bp:
                # Fallback euristico da collezione+numero (spesso ambiguo per
                # Pokémon): solo se inequivocabile, altrimenti niente push.
                bp = resolve_single(
                    article.card_collection,
                    article.card_number,
                    article.title,
                    _default_game_id(db),
                )
            if not bp:
                LOGGER.info(
                    "Auto-push CardTrader saltato: articolo %s carta ma blueprint "
                    "non individuato univocamente", article.id,
                )
                return {
                    "status": "unmatched",
                    "reason": "blueprint non individuato: controlla espansione e numero",
                }
            article.cardtrader_blueprint_id = bp
            db.commit()
            LOGGER.info("Auto-match blueprint %s per articolo %s", bp, article.id)
        res = publish_article(db, article)
        LOGGER.info(
            "Auto-push CardTrader: articolo %s → prodotto %s a %.2f€",
            article.id, res["product_id"], res["price_eur"],
        )
        return {
            "status": "published",
            "product_id": res["product_id"],
            "price_eur": res["price_eur"],
            "blueprint_id": article.cardtrader_blueprint_id,
        }
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Auto-push CardTrader fallito per articolo %s: %s", article.id, exc)
        return {"status": "error", "reason": str(exc)}


def _prodotti_collegati(db) -> set:
    from models.db import PersonalCard
    ids = {r[0] for r in db.query(Article.cardtrader_product_id)
           .filter(Article.cardtrader_product_id.isnot(None)).all()}
    ids |= {r[0] for r in db.query(PersonalCard.cardtrader_product_id)
            .filter(PersonalCard.cardtrader_product_id.isnot(None)).all()}
    return ids


def collega_prodotti(db, prodotti: Optional[List[dict]] = None, venduto: Optional[Article] = None) -> int:
    """Articoli con il blueprint ma senza prodotto CardTrader (messi in
    vendita a mano su CardTrader): si collegano al prodotto del nostro
    inventario con lo stesso blueprint, cosi' alla vendita si tolgono anche
    da li'. Solo se l'abbinamento e' certo: un solo articolo disponibile e
    un solo prodotto libero per quel blueprint. `venduto`: l'articolo
    appena venduto, che conta anche se non e' piu' disponibile."""
    from models.db import ArticleStatus
    articoli = (db.query(Article)
                .filter(Article.cardtrader_blueprint_id.isnot(None),
                        Article.cardtrader_product_id.is_(None),
                        Article.status == ArticleStatus.PUBLISHED).all())
    if venduto is not None and venduto not in articoli:
        articoli.append(venduto)
    if not articoli:
        return 0
    if prodotti is None:
        prodotti = ct.my_products()
    collegati = _prodotti_collegati(db)
    liberi: Dict[int, List[int]] = {}
    for p in prodotti:
        if p.get("id") and p["id"] not in collegati:
            liberi.setdefault(p.get("blueprint_id"), []).append(p["id"])
    per_blueprint: Dict[int, List[Article]] = {}
    for a in articoli:
        per_blueprint.setdefault(a.cardtrader_blueprint_id, []).append(a)
    n = 0
    for blueprint, gruppo in per_blueprint.items():
        trovati = liberi.get(blueprint, [])
        if len(gruppo) == 1 and len(trovati) == 1:
            gruppo[0].cardtrader_product_id = trovati[0]
            LOGGER.info("CardTrader: articolo %s collegato al prodotto %s (blueprint %s)",
                        gruppo[0].id, trovati[0], blueprint)
            n += 1
    if n:
        db.commit()
    return n


def auto_unpublish_on_sold(db, article: Article, piattaforma: str = "sito") -> None:
    """Hook alla vendita: toglie la carta da CardTrader per non venderla
    due volte. Best-effort."""
    try:
        if (not article.cardtrader_product_id and article.cardtrader_blueprint_id
                and ct.is_configured()):
            # Messa su CardTrader a mano e non ancora collegata dal job.
            collega_prodotti(db, ct.my_products(article.cardtrader_blueprint_id), venduto=article)
            db.refresh(article)
        if article.cardtrader_product_id and ct.is_configured():
            unpublish_article(db, article)
            LOGGER.info("Auto-unpublish CardTrader su vendita: articolo %s", article.id)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Auto-unpublish CardTrader fallito per articolo %s: %s", article.id, exc)
    # Articolo su eBay (inserzione propria, non della collezione carte):
    # venduto altrove, l'inserzione si ritira.
    from utils.article_ebay import on_sold_elsewhere
    on_sold_elsewhere(db, article)
    # Carta della collezione venduta sul sito: venduta anche li', e via
    # dalle sue inserzioni CardTrader/eBay.
    try:
        from utils.card_listing import on_article_sold
        on_article_sold(db, article, piattaforma)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        LOGGER.warning("Carta della collezione non aggiornata per articolo %s: %s", article.id, exc)
