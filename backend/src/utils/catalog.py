"""
Catalogo pubblico: ricerca, filtri e conteggi lato server.

Prima la home scaricava tutto il catalogo e filtrava nel browser: con 321
articoli erano ~650 KB, con qualche migliaio la pagina diventava pesante.
Ora il browser chiede una pagina alla volta e i conteggi dei filtri
("Carte 236") arrivano gia' fatti.

Le regole sono quelle che stavano in CatalogSection.tsx, per non cambiare
cosa vede chi cerca:
  - la ricerca e' "contiene", senza maiuscole, su titolo, descrizione,
    marca, modello e nomi di categoria;
  - il conteggio di un'opzione applica tutti gli ALTRI filtri piu' quella
    opzione (il classico facet count: "Pokemon (3)").

Per filtrare servono poche colonne, lette per tutti gli articoli pubblicati;
gli articoli completi si caricano solo per la pagina richiesta.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from models.db import Article, ArticleStatus, Category

SORT = ("recent", "price_asc", "price_desc", "title")


@dataclass
class Filtri:
    search: str = ""
    category: Optional[str] = None      # slug top-level
    subcategory: Optional[str] = None   # slug sottocategoria
    condition: Optional[str] = None
    brand: Optional[str] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None


@dataclass
class _Riga:
    id: int
    price: Decimal
    condition: str
    brand: Optional[str]
    top: Optional[str]          # slug top-level
    top_name: Optional[str]
    sub: Optional[str]          # slug sottocategoria (None se solo top)
    sub_name: Optional[str]
    testo: str = field(repr=False, default="")
    title: str = ""


def _righe(db: Session) -> List[_Riga]:
    cat = {c.id: c for c in db.query(Category).all()}
    q = (db.query(Article.id, Article.title, Article.description, Article.brand, Article.model,
                  Article.condition, Article.price, Article.category_id)
         .filter(Article.status == ArticleStatus.PUBLISHED, Article.reserved_order_id.is_(None))
         .order_by(asc(Article.display_order), desc(Article.created_at)))
    righe = []
    for id_, title, descr, brand, model, cond, price, cat_id in q.all():
        c = cat.get(cat_id)
        padre = cat.get(c.parent_id) if c is not None and c.parent_id else None
        top, sub = (padre, c) if padre is not None else (c, None)
        testo = " ".join(x for x in (title, descr, brand, model,
                                     c.name if c else None, padre.name if padre else None) if x).lower()
        righe.append(_Riga(
            id=id_, price=Decimal(str(price or 0)), condition=getattr(cond, "value", cond),
            brand=brand, top=top.slug if top else None, top_name=top.name if top else None,
            sub=sub.slug if sub else None, sub_name=sub.name if sub else None,
            testo=testo, title=title or "",
        ))
    return righe


def _passa(r: _Riga, f: Filtri, escludi: Optional[str] = None) -> bool:
    """Tutti i filtri, tranne la dimensione `escludi` (per i conteggi)."""
    if escludi != "search" and f.search.strip() and f.search.strip().lower() not in r.testo:
        return False
    if escludi != "category" and f.category and r.top != f.category:
        return False
    if escludi != "subcategory" and f.subcategory and r.sub != f.subcategory:
        return False
    if escludi != "condition" and f.condition and r.condition != f.condition:
        return False
    if escludi != "brand" and f.brand and r.brand != f.brand:
        return False
    if escludi != "price":
        if f.min_price is not None and r.price < f.min_price:
            return False
        if f.max_price is not None and r.price > f.max_price:
            return False
    return True


def _conta(righe: List[_Riga], f: Filtri, dim: str, chiave) -> Tuple[Dict[str, int], int]:
    """Conteggi per opzione della dimensione `dim` e totale ("Tutte")."""
    conti: Dict[str, int] = {}
    totale = 0
    for r in righe:
        if not _passa(r, f, escludi=dim):
            continue
        totale += 1
        k = chiave(r)
        if k:
            conti[k] = conti.get(k, 0) + 1
    return conti, totale


def cerca(db: Session, f: Filtri, sort: str = "recent", skip: int = 0, limit: int = 24) -> dict:
    righe = _righe(db)
    trovate = [r for r in righe if _passa(r, f)]
    if sort == "price_asc":
        trovate.sort(key=lambda r: r.price)
    elif sort == "price_desc":
        trovate.sort(key=lambda r: r.price, reverse=True)
    elif sort == "title":
        trovate.sort(key=lambda r: r.title.lower())

    # Nomi delle opzioni: da tutto il catalogo, come prima (un'opzione a 0
    # resta visibile, spenta, invece di sparire).
    nomi_cat = {r.top: r.top_name for r in righe if r.top}
    cat_conti, cat_tot = _conta(righe, f, "category", lambda r: r.top)
    cond_conti, cond_tot = _conta(righe, f, "condition", lambda r: r.condition)
    brand_conti, brand_tot = _conta(righe, f, "brand", lambda r: r.brand)
    sub_conti: Dict[str, int] = {}
    sub_nomi: Dict[str, str] = {}
    sub_tot = 0
    if f.category:
        sub_nomi = {r.sub: r.sub_name for r in righe if r.top == f.category and r.sub}
        sub_conti, sub_tot = _conta(righe, f, "subcategory", lambda r: r.sub)
    prezzi = [r.price for r in righe]

    pagina = trovate[skip:skip + limit]
    per_id = {a.id: a for a in db.query(Article).filter(Article.id.in_([r.id for r in pagina])).all()}
    return {
        "items": [per_id[r.id] for r in pagina if r.id in per_id],
        "total": len(trovate),
        "facets": {
            "categories": {s: {"name": nomi_cat[s], "count": cat_conti.get(s, 0)} for s in sorted(nomi_cat)},
            "total_all_categories": cat_tot,
            "subcategories": {s: {"name": sub_nomi[s], "count": sub_conti.get(s, 0)} for s in sorted(sub_nomi)},
            "total_all_subcategories": sub_tot,
            "conditions": {c: cond_conti.get(c, 0) for c in sorted({r.condition for r in righe})},
            "total_all_conditions": cond_tot,
            "brands": {b: n for b, n in sorted(brand_conti.items(), key=lambda x: -x[1])[:8]},
            "total_all_brands": brand_tot,
            "price_min": int(min(prezzi)) if prezzi else 0,
            "price_max": int(-(-max(prezzi) // 1)) if prezzi else 0,
        },
    }
