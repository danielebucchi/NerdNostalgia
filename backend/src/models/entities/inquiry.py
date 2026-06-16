"""
Entities Pydantic per le richieste di contatto.
"""
import enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class InquiryStatus(str, enum.Enum):
    NEW = "NEW"
    READ = "READ"
    REPLIED = "REPLIED"
    CLOSED = "CLOSED"


class InquiryCreate(BaseModel):
    article_id: Optional[int] = Field(None, description="ID articolo a cui si riferisce")
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    subject: Optional[str] = Field(None, max_length=255)
    message: str = Field(..., min_length=5, max_length=4000)


class InquiryUpdate(BaseModel):
    status: Optional[InquiryStatus] = None
    admin_notes: Optional[str] = None


class InquiryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    article_id: Optional[int]
    name: str
    email: str
    phone: Optional[str]
    subject: Optional[str]
    message: str
    status: InquiryStatus
    admin_notes: Optional[str]
    created_at: str
    updated_at: str
    replied_at: Optional[str]


class InquiryListResponse(BaseModel):
    items: List[InquiryResponse]
    total: int
    skip: int
    limit: int
