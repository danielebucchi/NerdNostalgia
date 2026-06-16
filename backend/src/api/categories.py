"""
API endpoint per le categorie (categoria/sottocategoria).
"""
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from helpers.auth import require_admin
from helpers.category import CategoryHelper, get_category_helper
from models.db import Category, User
from models.entities.category import (
    CategoryCreate,
    CategoryListResponse,
    CategoryNode,
    CategoryResponse,
    CategoryTreeResponse,
    CategoryUpdate,
)

router = APIRouter(prefix="/api/categories", tags=["categories"])


def _to_response(category: Category) -> CategoryResponse:
    return CategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        parent_id=category.parent_id,
        display_order=category.display_order,
    )


def _build_tree(categories: List[Category]) -> List[CategoryNode]:
    """Costruisce l'albero a partire dalla lista piatta gia' ordinata."""
    by_id: Dict[int, CategoryNode] = {
        c.id: CategoryNode(
            id=c.id,
            name=c.name,
            slug=c.slug,
            parent_id=c.parent_id,
            display_order=c.display_order,
            children=[],
        )
        for c in categories
    }
    roots: List[CategoryNode] = []
    for c in categories:
        node = by_id[c.id]
        if c.parent_id is None:
            roots.append(node)
        else:
            parent = by_id.get(c.parent_id)
            if parent is not None:
                parent.children.append(node)
            else:
                roots.append(node)
    return roots


@router.get("/", response_model=CategoryListResponse)
def list_categories(
    helper: CategoryHelper = Depends(get_category_helper),
):
    """Lista piatta di tutte le categorie (ordinate per parent + display_order)."""
    items = helper.gets()
    return CategoryListResponse(
        items=[_to_response(c) for c in items],
        total=len(items),
    )


@router.get("/tree", response_model=CategoryTreeResponse)
def list_categories_tree(
    helper: CategoryHelper = Depends(get_category_helper),
):
    """Albero gerarchico: top-level + children annidati."""
    items = helper.gets()
    return CategoryTreeResponse(items=_build_tree(items))


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    helper: CategoryHelper = Depends(get_category_helper),
    _admin: User = Depends(require_admin),
):
    existing = helper.get_by_slug(payload.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Slug '{payload.slug}' gia' utilizzato",
        )
    if payload.parent_id is not None:
        parent = helper.get(payload.parent_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parent {payload.parent_id} non trovato",
            )
        if parent.parent_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gerarchia limitata a 2 livelli (categoria/sottocategoria)",
            )
    category = Category(
        name=payload.name.strip(),
        slug=payload.slug.strip().lower(),
        parent_id=payload.parent_id,
        display_order=payload.display_order,
    )
    helper.save(category)
    return _to_response(category)


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    helper: CategoryHelper = Depends(get_category_helper),
    _admin: User = Depends(require_admin),
):
    category = helper.get(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Categoria {category_id} non trovata",
        )
    if payload.slug and payload.slug != category.slug:
        clash = helper.get_by_slug(payload.slug)
        if clash and clash.id != category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Slug '{payload.slug}' gia' utilizzato",
            )
    if payload.parent_id is not None:
        if payload.parent_id == category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="parent_id non puo' essere uguale all'id",
            )
        parent = helper.get(payload.parent_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parent {payload.parent_id} non trovato",
            )
        if parent.parent_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gerarchia limitata a 2 livelli",
            )
    helper.update(payload, category)
    return _to_response(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    helper: CategoryHelper = Depends(get_category_helper),
    _admin: User = Depends(require_admin),
):
    category = helper.get(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Categoria {category_id} non trovata",
        )
    helper.delete(category)
    return None
