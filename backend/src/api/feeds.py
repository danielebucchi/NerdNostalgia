"""
Feed prodotti per Google Merchant Center (schede gratuite su Google Shopping).

Google legge questo file da solo, una volta al giorno: ogni articolo in
vendita sul sito compare nella scheda "Shopping" con foto e prezzo, e chi
cerca "Charizard set base" vede direttamente il nostro. L'indirizzo da dare
a Merchant Center e' https://api.nerdnostalgia.store/api/feeds/google.xml.

Solo cio' che si puo' comprare adesso: pubblicato, non prenotato, con
quantita', prezzo e almeno una foto (Google scarta i prodotti senza). La
spedizione si imposta nell'account Merchant Center, non qui.
"""
import os
import re
from typing import List, Optional
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from models.db import Article, ArticleCondition, ArticleStatus
from utils.session import get_db

router = APIRouter(prefix="/api/feeds", tags=["feeds"])

CONDIZIONI_GOOGLE = {
    ArticleCondition.NEW: "new",
    ArticleCondition.REFURBISHED: "refurbished",
    ArticleCondition.USED: "used",
    ArticleCondition.FOR_PARTS: "used",
}
MAX_TITOLO = 150
MAX_DESCRIZIONE = 5000
MAX_FOTO_EXTRA = 10


def _site_url() -> str:
    return (os.getenv("SITE_PUBLIC_URL") or os.getenv("NEXT_PUBLIC_SITE_URL")
            or "https://nerdnostalgia.store").rstrip("/")


def _api_url() -> str:
    return (os.getenv("BASE_URL") or "https://api.nerdnostalgia.store").rstrip("/")


def _assoluto(url: str) -> Optional[str]:
    """Google vuole URL completi: le foto salvate come /static/... prendono
    il dominio dell'API, che e' chi le serve."""
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"{_api_url()}/{url.lstrip('/')}"


def _testo(s: Optional[str], massimo: int) -> str:
    return re.sub(r"\s+", " ", s or "").strip()[:massimo]


def _categoria(article: Article) -> Optional[str]:
    """La categoria del sito, es. "Carte > Pokémon": Google la usa per
    raggruppare, la categoria Google la deduce da solo."""
    cat = article.category
    if cat is None:
        return None
    padre = cat.parent if cat.parent_id else None
    return f"{padre.name} > {cat.name}" if padre is not None else cat.name


# Le sottocategorie che sono anche una marca. Le altre (Console, Giochi,
# Peluche...) no: meglio nessuna marca che una sbagliata. Stessa tabella in
# frontend/src/lib/seo.ts (BRAND_BY_CATEGORY).
MARCA_DA_CATEGORIA = {
    "Pokémon": "Pokémon",
    "Magic the Gathering": "Magic: The Gathering",
    "Yu-Gi-Oh!": "Yu-Gi-Oh!",
    "Funko Pop": "Funko",
    "Gormiti": "Gormiti",
    "Bakugan": "Bakugan",
    "Beyblade": "Beyblade",
}


def _marca(article: Article) -> Optional[str]:
    """La marca, o quella della sottocategoria (Pokémon, Funko, Gormiti...):
    senza codice EAN Google la chiede."""
    marca = _testo(article.brand, 70)
    if marca:
        return marca
    cat = article.category
    return MARCA_DA_CATEGORIA.get(cat.name) if cat is not None else None


def _voce(article: Article) -> Optional[str]:
    foto = [u for u in (_assoluto(x) for x in (article.images or [])) if u]
    if not foto or not article.price or float(article.price) <= 0:
        return None
    campi = [
        ("g:id", f"nn-{article.id}"),
        ("g:title", _testo(article.title, MAX_TITOLO)),
        ("g:description", _testo(article.description, MAX_DESCRIZIONE) or _testo(article.title, MAX_TITOLO)),
        ("g:link", f"{_site_url()}/articles/{article.id}"),
        ("g:image_link", foto[0]),
        *[("g:additional_image_link", u) for u in foto[1:1 + MAX_FOTO_EXTRA]],
        ("g:availability", "in_stock"),
        ("g:price", f"{float(article.price):.2f} {article.currency or 'EUR'}"),
        ("g:condition", CONDIZIONI_GOOGLE.get(article.condition, "used")),
        ("g:product_type", _categoria(article)),
        ("g:brand", _marca(article)),
        # Pezzi usati e da collezione: niente codice EAN/GTIN.
        ("g:identifier_exists", "no"),
    ]
    righe = "".join(f"      <{k}>{escape(v)}</{k}>\n" for k, v in campi if v)
    return f"    <item>\n{righe}    </item>\n"


def feed_google(db: Session) -> str:
    articoli: List[Article] = (
        db.query(Article)
        .filter(Article.status == ArticleStatus.PUBLISHED,
                Article.reserved_order_id.is_(None),
                Article.quantity > 0)
        .order_by(Article.id)
        .all()
    )
    voci = "".join(v for v in (_voce(a) for a in articoli) if v)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">\n'
        "  <channel>\n"
        "    <title>NerdNostalgia</title>\n"
        f"    <link>{escape(_site_url())}</link>\n"
        "    <description>Videogiochi vintage, carte Pokémon e nerderie</description>\n"
        f"{voci}"
        "  </channel>\n"
        "</rss>\n"
    )


@router.get("/google.xml")
def google_feed(db: Session = Depends(get_db)):
    """Pubblico: Google lo scarica senza autenticazione."""
    return Response(content=feed_google(db), media_type="application/xml; charset=utf-8",
                    headers={"Cache-Control": "public, max-age=3600"})
