import enum
from typing import Optional

from pydantic import BaseModel, Field, EmailStr


class UserRole(enum.Enum):
    ADMIN = "ADMIN"
    USER = "USER"
    GUEST = "GUEST"


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100, description="Username univoco")
    email: EmailStr = Field(..., description="Email univoca")
    password: str = Field(..., min_length=6, description="Password (min 6 caratteri)")
    full_name: Optional[str] = Field(None, max_length=255, description="Nome completo")
    role: Optional[UserRole] = Field(None, description="Ruolo: ADMIN, USER, GUEST")


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
