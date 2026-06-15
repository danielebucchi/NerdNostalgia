"""
Helper per la gestione degli articoli.
"""
import datetime
from datetime import datetime as dt
from decimal import Decimal
from typing import List, Optional, Tuple

from fastapi import Depends
from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session

from helpers import BaseHelper
from models.db import Article, ArticleCondition, ArticleStatus
from models.entities.article import ArticleUpdate
from utils.session import get_db


class ArticleHelper(BaseHelper):

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get(self, field: str, value) -> Optional[Article]:
        if not hasattr(Article, field):
            raise ValueError(f"Il campo '{field}' non esiste nel modello Article")
        return self.db.query(Article).filter(getattr(Article, field) == value).first()

    def gets(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[ArticleStatus] = None,
        category: Optional[str] = None,
        condition: Optional[ArticleCondition] = None,
        brand: Optional[str] = None,
        user_id: Optional[int] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Article], int]:
        query = self.db.query(Article)

        if status is not None:
            query = query.filter(Article.status == status)
        if category:
            query = query.filter(Article.category == category)
        if condition is not None:
            query = query.filter(Article.condition == condition)
        if brand:
            query = query.filter(Article.brand == brand)
        if user_id is not None:
            query = query.filter(Article.user_id == user_id)
        if min_price is not None:
            query = query.filter(Article.price >= min_price)
        if max_price is not None:
            query = query.filter(Article.price <= max_price)
        if search:
            tsvector = func.to_tsvector(
                "italian",
                func.coalesce(Article.title, "") + " " + func.coalesce(Article.description, ""),
            )
            tsquery = func.plainto_tsquery("italian", search)
            query = query.filter(tsvector.op("@@")(tsquery))

        total = query.count()
        items = (
            query.order_by(asc(Article.display_order), desc(Article.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total

    def reorder(self, ordered_ids: List[int]) -> None:
        """Imposta display_order in base alla posizione nella lista (0..n-1)."""
        for position, article_id in enumerate(ordered_ids):
            article = self.get("id", article_id)
            if article is not None:
                article.display_order = position
        self.db.commit()

    def save(self, article: Article) -> None:
        self.db.add(article)
        self.db.commit()
        self.db.refresh(article)

    def update(self, new_data: ArticleUpdate, existing: Article) -> None:
        update_data = new_data.model_dump(exclude_unset=True)
        previous_status = existing.status

        for key, value in update_data.items():
            setattr(existing, key, value)

        if "status" in update_data and existing.status != previous_status:
            if existing.status == ArticleStatus.PUBLISHED and not existing.published_at:
                existing.published_at = dt.now(datetime.UTC)
            if existing.status == ArticleStatus.SOLD and not existing.sold_at:
                existing.sold_at = dt.now(datetime.UTC)

        existing.updated_at = dt.now(datetime.UTC)
        self.db.commit()
        self.db.refresh(existing)

    def delete(self, article: Article) -> None:
        self.db.delete(article)
        self.db.commit()

    def set_status(self, article: Article, new_status: ArticleStatus) -> None:
        article.status = new_status
        now = dt.now(datetime.UTC)
        if new_status == ArticleStatus.PUBLISHED and not article.published_at:
            article.published_at = now
        if new_status == ArticleStatus.SOLD and not article.sold_at:
            article.sold_at = now
        article.updated_at = now
        self.db.commit()
        self.db.refresh(article)

    def add_image(self, article: Article, url: str) -> None:
        images = list(article.images or [])
        if url not in images:
            images.append(url)
        article.images = images
        article.updated_at = dt.now(datetime.UTC)
        self.db.commit()
        self.db.refresh(article)

    def remove_image(self, article: Article, url: str) -> None:
        images = [u for u in (article.images or []) if u != url]
        article.images = images
        article.updated_at = dt.now(datetime.UTC)
        self.db.commit()
        self.db.refresh(article)


def get_article_helper(db: Session = Depends(get_db)) -> ArticleHelper:
    return ArticleHelper(db=db)
