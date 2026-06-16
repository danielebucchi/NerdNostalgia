"""
Entities Pydantic per le categorie.
"""
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")
    parent_id: Optional[int] = None
    display_order: int = Field(0, ge=0)


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    slug: Optional[str] = Field(None, min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")
    parent_id: Optional[int] = None
    display_order: Optional[int] = Field(None, ge=0)


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    parent_id: Optional[int]
    display_order: int


class CategoryNode(CategoryResponse):
    """Categoria con i figli annidati (usata dall'endpoint /tree)."""
    children: List["CategoryNode"] = Field(default_factory=list)


CategoryNode.model_rebuild()


class CategoryListResponse(BaseModel):
    items: List[CategoryResponse]
    total: int


class CategoryTreeResponse(BaseModel):
    items: List[CategoryNode]
