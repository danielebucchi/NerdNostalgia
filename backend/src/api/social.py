"""Instagram (vedi utils/instagram.py).

GET  /api/social/instagram/{id}/{post|storia}.jpg — pubblico: l'immagine che
     Instagram scarica per pubblicare, solo per articoli in vendita.
GET  /api/social/instagram/status   — admin: configurazione e cosa uscira'.
POST /api/social/instagram/run      — admin: pubblica subito carosello o Storie.
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from helpers.auth import require_admin
from models.db import Article, ArticleStatus, User
from utils import instagram
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
        "caption": instagram.didascalia(instagram.da_carosello(db)) if instagram.da_carosello(db) else None,
        # Se oggi non ci sono novita', esce questo.
        "fallback": (_voce(instagram.da_ripescare(db), "post") if instagram.da_ripescare(db) else None),
    }


class RunRequest(BaseModel):
    what: Literal["carousel", "stories"]


@router.post("/instagram/run")
def run(payload: RunRequest, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    if not instagram.acceso(db):
        raise HTTPException(status_code=409, detail="Instagram non configurato o spento in Impostazioni.")
    try:
        if payload.what == "carousel":
            return {"carousel": instagram.pubblica_carosello(db)}
        return {"stories": instagram.pubblica_storie(db)}
    except instagram.ErroreInstagram as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
