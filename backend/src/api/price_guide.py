"""Guida prezzi delle carte Pokémon (utils/price_guide.py), pubblica.

GET /api/price-guide/sets                      — i set, dal piu' recente
GET /api/price-guide/sets/{slug}               — un set con tutte le carte
GET /api/price-guide/cards/{set_slug}/{slug}   — una carta, le altre versioni, se l'abbiamo
GET /api/price-guide/search?q=charizard        — "Valuta la tua carta"
GET /api/price-guide/sitemap                   — gli indirizzi per la sitemap
POST /api/price-guide/refresh                  — admin: aggiorna subito (in background)
"""
import threading
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from helpers.auth import require_admin
from models.db import PriceGuideCard, PriceGuideSet, User
from utils import price_guide as pg
from utils.limiter import limiter
from utils.session import SessionLocal, get_db

router = APIRouter(prefix="/api/price-guide", tags=["price-guide"])

CACHE = {"Cache-Control": "public, max-age=3600"}


def _set(s: PriceGuideSet, carte: Optional[int] = None) -> dict:
    return {"slug": s.slug, "name": s.nome, "name_en": s.name_en, "release_date": s.release_date,
            "card_count": s.card_count, "serie": s.serie, "logo": s.logo_url,
            "cards_priced": carte, "updated_at": s.updated_at.isoformat() if s.updated_at else None}


def _carta(c: PriceGuideCard, disponibile: Optional[dict] = None, regola: Optional[dict] = None) -> dict:
    """min_price e buy_* sono per il prezzo in evidenza (Near Mint, italiana
    se c'e'); prices ha il prezzo e l'offerta per lingua e condizione:
    {"it": {"NM": {"price": 551.28, "buy_offer": ..., "buy_bulk": ..., "buy_none": ...}}}."""
    tabella = {}
    for lingua, righe in (c.prices or {}).items():
        tabella[lingua] = {s: {"price": pg.euro(cent), **_offerta(c, cent, regola)} for s, cent in righe.items()}
    return {"slug": c.slug, "set_slug": c.set.slug, "set_name": c.set.nome, "number": c.number,
            "name": c.nome, "name_en": c.name_en, "image": c.image_url, "min_price": pg.euro(c.min_price_cents),
            "offers": c.offers, "available": disponibile, "prices": tabella,
            **_offerta(c, c.min_price_cents, regola)}


def _offerta(c: PriceGuideCard, centesimi: Optional[int], regola: Optional[dict]) -> dict:
    """buy_offer: euro per la carta singola; buy_bulk: {epoca, euro_kg} se va a peso;
    buy_none: True se non la compriamo (energie a peso)."""
    if not regola:
        return {"buy_offer": None, "buy_bulk": None, "buy_none": False}
    o = pg.offerta(centesimi, regola, c.set.release_date, c.name_en)
    return {"buy_offer": o.get("euro"),
            "buy_bulk": {"era": o["epoca"], "eur_per_kg": o["euro_kg"]} if o.get("tipo") == "peso" else None,
            "buy_none": o.get("tipo") == "no"}


@router.get("/sets")
def sets(db: Session = Depends(get_db)):
    conteggi = dict(db.query(PriceGuideCard.set_id, func.count(PriceGuideCard.id))
                    .filter(PriceGuideCard.min_price_cents.isnot(None)).group_by(PriceGuideCard.set_id).all())
    righe = db.query(PriceGuideSet).order_by(PriceGuideSet.release_date.desc()).all()
    return JSONResponse([_set(s, conteggi.get(s.id, 0)) for s in righe if conteggi.get(s.id)], headers=CACHE)


@router.get("/sets/{slug}")
def set_dettaglio(slug: str, db: Session = Depends(get_db)):
    s = db.query(PriceGuideSet).filter(PriceGuideSet.slug == slug).first()
    if s is None:
        raise HTTPException(status_code=404, detail="Set non trovato")
    carte = sorted(s.cards, key=lambda c: (int(c.number) if c.number.isdigit() else 10**6, c.number, c.slug))
    nostre = pg.disponibili(db, [c.blueprint_id for c in carte])
    regola = pg.regola_offerta(db)
    return JSONResponse({**_set(s, sum(1 for c in carte if c.min_price_cents)),
                         "cards": [_carta(c, nostre.get(c.blueprint_id), regola) for c in carte]}, headers=CACHE)


@router.get("/cards/{set_slug}/{slug}")
def carta(set_slug: str, slug: str, db: Session = Depends(get_db)):
    c = (db.query(PriceGuideCard).join(PriceGuideSet)
         .filter(PriceGuideSet.slug == set_slug, PriceGuideCard.slug == slug).first())
    if c is None:
        raise HTTPException(status_code=404, detail="Carta non trovata")
    # La stessa carta in altri set (ristampe, promo): utili da confrontare.
    altre = (db.query(PriceGuideCard).filter(PriceGuideCard.name_en == c.name_en, PriceGuideCard.id != c.id,
                                             PriceGuideCard.min_price_cents.isnot(None))
             .order_by(PriceGuideCard.min_price_cents.desc()).limit(12).all())
    nostre = pg.disponibili(db, [c.blueprint_id] + [a.blueprint_id for a in altre])
    regola = pg.regola_offerta(db)
    return JSONResponse({**_carta(c, nostre.get(c.blueprint_id), regola), "set": _set(c.set),
                         "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                         "other_versions": [_carta(a, nostre.get(a.blueprint_id), regola) for a in altre]},
                        headers=CACHE)


@router.get("/search")
@limiter.limit("60/minute")
def cerca(request: Request, q: str = Query(..., min_length=2, max_length=80), db: Session = Depends(get_db)):
    parole = [p for p in q.strip().split() if p]
    query = db.query(PriceGuideCard).join(PriceGuideSet)
    for p in parole:
        like = f"%{p}%"
        query = query.filter(or_(PriceGuideCard.name_en.ilike(like), PriceGuideCard.name_it.ilike(like),
                                 PriceGuideSet.name_en.ilike(like), PriceGuideSet.name_it.ilike(like),
                                 PriceGuideCard.number == p.lstrip("0")))
    risultati = (query.filter(PriceGuideCard.min_price_cents.isnot(None))
                 .order_by(PriceGuideCard.min_price_cents.desc()).limit(30).all())
    nostre = pg.disponibili(db, [c.blueprint_id for c in risultati])
    regola = pg.regola_offerta(db)
    return [_carta(c, nostre.get(c.blueprint_id), regola) for c in risultati]


@router.get("/sitemap")
def sitemap(db: Session = Depends(get_db)):
    sets_ = {s.id: s for s in db.query(PriceGuideSet).all()}
    carte = (db.query(PriceGuideCard.set_id, PriceGuideCard.slug, PriceGuideCard.updated_at)
             .filter(PriceGuideCard.min_price_cents.isnot(None)).all())
    con_carte = {set_id for set_id, _, _ in carte}
    # Compatta: con ventimila carte ogni byte conta (la cache di Next.js
    # rifiuta le risposte sopra i 2 MB). La data e' quella del set.
    return JSONResponse({
        "sets": [{"slug": s.slug, "updated_at": s.updated_at.date().isoformat()}
                 for i, s in sets_.items() if i in con_carte],
        "cards": [[sets_[set_id].slug, slug_] for set_id, slug_, _ in carte if set_id in sets_],
    }, headers=CACHE)


def _aggiorna_in_background() -> None:
    db = SessionLocal()
    try:
        pg.aggiorna(db)
    finally:
        db.close()


@router.post("/refresh")
def refresh(_admin: User = Depends(require_admin)):
    threading.Thread(target=_aggiorna_in_background, daemon=True).start()
    return {"started": True}
