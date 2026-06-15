"""
API endpoint per gli articoli.
"""
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from helpers.article import ArticleHelper, get_article_helper
from helpers.user import UserHelper, get_user_helper
from models.db import Article, ArticleCondition, ArticleStatus
from models.entities.article import (
    ArticleCreate,
    ArticleImageAdd,
    ArticleListResponse,
    ArticleResponse,
    ArticleUpdate,
)

router = APIRouter(prefix="/api/articles", tags=["articles"])


def _to_response(article: Article) -> ArticleResponse:
    return ArticleResponse(
        id=article.id,
        user_id=article.user_id,
        title=article.title,
        description=article.description,
        price=article.price,
        currency=article.currency,
        category=article.category,
        condition=article.condition.value,
        status=article.status.value,
        quantity=article.quantity,
        sku=article.sku,
        brand=article.brand,
        model=article.model,
        weight_kg=article.weight_kg,
        dimensions_cm=article.dimensions_cm,
        images=article.images or [],
        article_metadata=article.article_metadata or {},
        created_at=article.created_at.isoformat() if article.created_at else None,
        updated_at=article.updated_at.isoformat() if article.updated_at else None,
        published_at=article.published_at.isoformat() if article.published_at else None,
        sold_at=article.sold_at.isoformat() if article.sold_at else None,
    )


@router.post("/", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
def create_article(
    article_data: ArticleCreate,
    article_helper: ArticleHelper = Depends(get_article_helper),
    user_helper: UserHelper = Depends(get_user_helper),
):
    """Crea un nuovo articolo."""
    owner = user_helper.get("id", article_data.user_id)
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Utente con ID {article_data.user_id} non trovato",
        )

    if article_data.sku:
        existing = article_helper.get("sku", article_data.sku)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SKU '{article_data.sku}' gia' utilizzato",
            )

    new_article = Article(
        user_id=article_data.user_id,
        title=article_data.title,
        description=article_data.description,
        price=article_data.price,
        currency=article_data.currency,
        category=article_data.category,
        condition=ArticleCondition(article_data.condition.value),
        status=ArticleStatus(article_data.status.value),
        quantity=article_data.quantity,
        sku=article_data.sku,
        brand=article_data.brand,
        model=article_data.model,
        weight_kg=article_data.weight_kg,
        dimensions_cm=article_data.dimensions_cm,
        images=article_data.images,
        article_metadata=article_data.article_metadata,
    )
    article_helper.save(new_article)
    return _to_response(new_article)


@router.get("/", response_model=ArticleListResponse)
def list_articles(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[ArticleStatus] = Query(None, alias="status"),
    category: Optional[str] = None,
    condition: Optional[ArticleCondition] = None,
    brand: Optional[str] = None,
    user_id: Optional[int] = None,
    min_price: Optional[Decimal] = Query(None, ge=0),
    max_price: Optional[Decimal] = Query(None, ge=0),
    search: Optional[str] = Query(None, description="Ricerca full-text su titolo e descrizione"),
    article_helper: ArticleHelper = Depends(get_article_helper),
):
    """Lista articoli con paginazione, filtri e ricerca full-text."""
    db_status = ArticleStatus(status_filter.value) if status_filter else None
    db_condition = ArticleCondition(condition.value) if condition else None

    items, total = article_helper.gets(
        skip=skip,
        limit=limit,
        status=db_status,
        category=category,
        condition=db_condition,
        brand=brand,
        user_id=user_id,
        min_price=min_price,
        max_price=max_price,
        search=search,
    )

    return ArticleListResponse(
        items=[_to_response(a) for a in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{article_id}", response_model=ArticleResponse)
def get_article(
    article_id: int,
    article_helper: ArticleHelper = Depends(get_article_helper),
):
    """Ottieni un articolo per ID."""
    article = article_helper.get("id", article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con ID {article_id} non trovato",
        )
    return _to_response(article)


@router.get("/sku/{sku}", response_model=ArticleResponse)
def get_article_by_sku(
    sku: str,
    article_helper: ArticleHelper = Depends(get_article_helper),
):
    """Ottieni un articolo per SKU."""
    article = article_helper.get("sku", sku)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con SKU '{sku}' non trovato",
        )
    return _to_response(article)


@router.patch("/{article_id}", response_model=ArticleResponse)
def update_article(
    article_id: int,
    article_data: ArticleUpdate,
    article_helper: ArticleHelper = Depends(get_article_helper),
):
    """Aggiorna un articolo."""
    article = article_helper.get("id", article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con ID {article_id} non trovato",
        )

    if article_data.sku and article_data.sku != article.sku:
        existing = article_helper.get("sku", article_data.sku)
        if existing and existing.id != article_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SKU '{article_data.sku}' gia' utilizzato",
            )

    article_helper.update(article_data, article)
    return _to_response(article)


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(
    article_id: int,
    article_helper: ArticleHelper = Depends(get_article_helper),
):
    """Elimina un articolo."""
    article = article_helper.get("id", article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con ID {article_id} non trovato",
        )
    article_helper.delete(article)
    return None


@router.post("/{article_id}/publish", response_model=ArticleResponse)
def publish_article(
    article_id: int,
    article_helper: ArticleHelper = Depends(get_article_helper),
):
    """Marca l'articolo come pubblicato."""
    article = article_helper.get("id", article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con ID {article_id} non trovato",
        )
    article_helper.set_status(article, ArticleStatus.PUBLISHED)
    return _to_response(article)


@router.post("/{article_id}/sell", response_model=ArticleResponse)
def sell_article(
    article_id: int,
    article_helper: ArticleHelper = Depends(get_article_helper),
):
    """Marca l'articolo come venduto."""
    article = article_helper.get("id", article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con ID {article_id} non trovato",
        )
    article_helper.set_status(article, ArticleStatus.SOLD)
    return _to_response(article)


@router.post("/{article_id}/archive", response_model=ArticleResponse)
def archive_article(
    article_id: int,
    article_helper: ArticleHelper = Depends(get_article_helper),
):
    """Marca l'articolo come archiviato."""
    article = article_helper.get("id", article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con ID {article_id} non trovato",
        )
    article_helper.set_status(article, ArticleStatus.ARCHIVED)
    return _to_response(article)


@router.post("/{article_id}/images", response_model=ArticleResponse)
def add_article_image(
    article_id: int,
    payload: ArticleImageAdd,
    article_helper: ArticleHelper = Depends(get_article_helper),
):
    """Aggiunge un URL immagine all'articolo."""
    article = article_helper.get("id", article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con ID {article_id} non trovato",
        )
    article_helper.add_image(article, payload.url)
    return _to_response(article)


@router.delete("/{article_id}/images", response_model=ArticleResponse)
def remove_article_image(
    article_id: int,
    url: str = Query(..., description="URL dell'immagine da rimuovere"),
    article_helper: ArticleHelper = Depends(get_article_helper),
):
    """Rimuove un URL immagine dall'articolo."""
    article = article_helper.get("id", article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Articolo con ID {article_id} non trovato",
        )
    article_helper.remove_image(article, url)
    return _to_response(article)
