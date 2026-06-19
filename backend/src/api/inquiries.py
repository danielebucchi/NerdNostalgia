"""
API endpoint per le richieste di contatto.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

import os

from helpers.article import ArticleHelper, get_article_helper
from helpers.auth import require_admin
from helpers.inquiry import InquiryHelper, get_inquiry_helper
from models.db import Inquiry, InquiryStatus, User
from models.entities.inquiry import (
    InquiryCreate,
    InquiryListResponse,
    InquiryResponse,
    InquiryUpdate,
)
from utils.email import send_inquiry_notification
from utils.limiter import limiter

router = APIRouter(prefix="/api/inquiries", tags=["inquiries"])


def _to_response(inquiry: Inquiry) -> InquiryResponse:
    return InquiryResponse(
        id=inquiry.id,
        article_id=inquiry.article_id,
        name=inquiry.name,
        email=inquiry.email,
        phone=inquiry.phone,
        subject=inquiry.subject,
        message=inquiry.message,
        status=inquiry.status.value,
        admin_notes=inquiry.admin_notes,
        created_at=inquiry.created_at.isoformat() if inquiry.created_at else None,
        updated_at=inquiry.updated_at.isoformat() if inquiry.updated_at else None,
        replied_at=inquiry.replied_at.isoformat() if inquiry.replied_at else None,
    )


@router.post("/", response_model=InquiryResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute;30/hour")
def submit_inquiry(
    data: InquiryCreate,
    request: Request,
    inquiry_helper: InquiryHelper = Depends(get_inquiry_helper),
    article_helper: ArticleHelper = Depends(get_article_helper),
):
    """Invia una richiesta di contatto. Endpoint pubblico (nessun auth).
    Rate limit: 5/min e 30/h per IP. Honeypot field 'website' scarta i bot."""
    # Honeypot: bot riempiono ogni campo, utenti veri lasciano questo vuoto.
    # Fingiamo successo per non rivelare il meccanismo.
    if data.website:
        from datetime import datetime
        now = datetime.utcnow().isoformat()
        return InquiryResponse(
            id=0,
            article_id=data.article_id,
            name=data.name,
            email=str(data.email),
            phone=data.phone,
            subject=data.subject,
            message=data.message,
            status="NEW",
            admin_notes=None,
            created_at=now,
            updated_at=now,
            replied_at=None,
        )

    article = None
    if data.article_id is not None:
        article = article_helper.get("id", data.article_id)
        if not article:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Articolo con ID {data.article_id} non trovato",
            )

    client_ip = request.client.host if request.client else None

    new_inquiry = Inquiry(
        article_id=data.article_id,
        name=data.name.strip(),
        email=str(data.email).lower().strip(),
        phone=data.phone.strip() if data.phone else None,
        subject=data.subject.strip() if data.subject else None,
        message=data.message.strip(),
        ip_address=client_ip,
    )
    inquiry_helper.save(new_inquiry)

    # Notifica all'admin via email (non-blocking)
    site_url = os.getenv("SITE_PUBLIC_URL", "").rstrip("/")
    article_url = (
        f"{site_url}/articles/{article.id}"
        if article and site_url else None
    )
    try:
        send_inquiry_notification(
            new_inquiry,
            article_title=article.title if article else None,
            article_url=article_url,
        )
    except Exception:  # noqa: BLE001
        # Mai bloccare la response sull'errore di mail
        pass

    return _to_response(new_inquiry)


@router.get("/", response_model=InquiryListResponse)
def list_inquiries(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_filter: Optional[InquiryStatus] = Query(None, alias="status"),
    article_id: Optional[int] = None,
    email: Optional[str] = None,
    inquiry_helper: InquiryHelper = Depends(get_inquiry_helper),
    _admin: User = Depends(require_admin),
):
    """Lista richieste (admin-only) con filtri."""
    db_status = InquiryStatus(status_filter.value) if status_filter else None
    items, total = inquiry_helper.gets(
        skip=skip,
        limit=limit,
        status=db_status,
        article_id=article_id,
        email=email,
    )
    return InquiryListResponse(
        items=[_to_response(i) for i in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{inquiry_id}", response_model=InquiryResponse)
def get_inquiry(
    inquiry_id: int,
    inquiry_helper: InquiryHelper = Depends(get_inquiry_helper),
    _admin: User = Depends(require_admin),
):
    """Dettaglio richiesta (admin-only)."""
    inquiry = inquiry_helper.get("id", inquiry_id)
    if not inquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Richiesta con ID {inquiry_id} non trovata",
        )
    # Auto-mark come letta se era NEW
    if inquiry.status == InquiryStatus.NEW:
        inquiry_helper.update(InquiryUpdate(status="READ"), inquiry)
    return _to_response(inquiry)


@router.patch("/{inquiry_id}", response_model=InquiryResponse)
def update_inquiry(
    inquiry_id: int,
    data: InquiryUpdate,
    inquiry_helper: InquiryHelper = Depends(get_inquiry_helper),
    _admin: User = Depends(require_admin),
):
    """Aggiorna richiesta (status, note admin)."""
    inquiry = inquiry_helper.get("id", inquiry_id)
    if not inquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Richiesta con ID {inquiry_id} non trovata",
        )
    inquiry_helper.update(data, inquiry)
    return _to_response(inquiry)


@router.delete("/{inquiry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inquiry(
    inquiry_id: int,
    inquiry_helper: InquiryHelper = Depends(get_inquiry_helper),
    _admin: User = Depends(require_admin),
):
    """Elimina richiesta (admin-only)."""
    inquiry = inquiry_helper.get("id", inquiry_id)
    if not inquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Richiesta con ID {inquiry_id} non trovata",
        )
    inquiry_helper.delete(inquiry)
    return None
