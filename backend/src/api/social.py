"""Instagram (vedi utils/instagram.py).

GET  /api/social/instagram/{id}/{post|storia}.jpg — pubblico: l'immagine che
     Instagram scarica per pubblicare, solo per articoli in vendita.
GET  /api/social/instagram/status   — admin: configurazione e cosa uscira'.
GET  /api/social/instagram/stats    — admin: copertura per orario e per hashtag, report.
POST /api/social/instagram/reel/preview — admin: monta il Reel di un mese senza pubblicarlo.
POST /api/social/instagram/run      — admin: pubblica subito carosello, Storie o Reel.
"""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from helpers.auth import require_admin
from models.db import Article, ArticleStatus, User
from utils import instagram, instagram_reel, instagram_stats
from utils.session import get_db

router = APIRouter(prefix="/api/social", tags=["social"])


@router.get("/instagram/{article_id}/{formato}.jpg")
def immagine(article_id: int, formato: Literal["post", "storia"], db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == article_id,
                                       Article.status == ArticleStatus.PUBLISHED).first()
    if article is None:
        raise HTTPException(status_code=404, detail="Articolo non trovato")
    return Response(content=instagram.immagine(article, formato), media_type="image/jpeg",
                    headers={"Cache-Control": "public, max-age=86400"})


def _voce(a: Article, formato: str) -> dict:
    return {"id": a.id, "title": a.title, "price": float(a.price or 0),
            "image": instagram.url_immagine(a, formato)}


@router.get("/instagram/status")
def status(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return {
        "configured": instagram.configurato(db),
        "enabled": instagram.acceso(db),
        "story_min_price": instagram.soglia_storie(db),
        "next_carousel": [_voce(a, "post") for a in instagram.da_carosello(db)],
        "next_stories": [_voce(a, "storia") for a in instagram.da_storie(db)],
        "caption": instagram.didascalia(instagram.da_carosello(db), db=db) if instagram.da_carosello(db) else None,
        # Se oggi non ci sono novita', esce questo.
        "fallback": (_voce(instagram.da_ripescare(db), "post") if instagram.da_ripescare(db) else None),
    }


@router.get("/instagram/stats")
def stats(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    from statistics import mean
    return {
        "slot_today": instagram_stats.slot_di_oggi(db),
        "reach_by_slot": {s: {"posts": len(v), "avg_reach": round(mean(v)) if v else None}
                          for s, v in instagram_stats.copertura_per_slot(db).items()},
        "top_hashtags": dict(sorted(instagram_stats.copertura_per_hashtag(db).items(),
                                    key=lambda kv: kv[1], reverse=True)[:15]),
        "report": (instagram_stats.report(db) or {}).get("text"),
    }


class ReelRequest(BaseModel):
    year: Optional[int] = None
    month: Optional[int] = None


@router.post("/instagram/reel/preview")
def reel_preview(payload: ReelRequest, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    anno, mese = (payload.year, payload.month) if payload.year and payload.month else instagram_reel.mese_precedente()
    esito = instagram_reel.anteprima(db, anno, mese)
    if esito is None:
        raise HTTPException(status_code=404, detail="Nessun articolo venduto in quel mese.")
    return esito


class RunRequest(BaseModel):
    what: Literal["carousel", "stories", "reel"]
    year: Optional[int] = None
    month: Optional[int] = None


@router.post("/instagram/run")
def run(payload: RunRequest, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    if not instagram.acceso(db):
        raise HTTPException(status_code=409, detail="Instagram non configurato o spento in Impostazioni.")
    try:
        if payload.what == "carousel":
            return {"carousel": instagram.pubblica_carosello(db)}
        if payload.what == "reel":
            return {"reel": instagram_reel.pubblica(db, payload.year, payload.month, forza=True)}
        return {"stories": instagram.pubblica_storie(db)}
    except instagram.ErroreInstagram as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
