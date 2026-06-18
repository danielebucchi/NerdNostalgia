"""Entities Pydantic per Platform."""
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


def _slugify(name: str) -> str:
    return (
        name.lower()
        .strip()
        .replace(" ", "-")
        .replace("/", "-")
        .replace("&", "and")
    )


class PlatformCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    slug: Optional[str] = Field(None, max_length=50)
    icon: Optional[str] = Field(None, max_length=10)
    display_order: int = 0
    is_active: bool = True
    note: Optional[str] = None


class PlatformUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    slug: Optional[str] = Field(None, max_length=50)
    icon: Optional[str] = Field(None, max_length=10)
    display_order: Optional[int] = None
    is_active: Optional[bool] = None
    note: Optional[str] = None


class PlatformResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    icon: Optional[str]
    display_order: int
    is_active: bool
    note: Optional[str]
    created_at: str
    updated_at: str


class PlatformListResponse(BaseModel):
    items: List[PlatformResponse]
    total: int
