"""
Rubrica indirizzi del cliente.

Serve a non far riscrivere via, CAP, citta' e telefono a ogni acquisto a
chi compra piu' di una volta. Gli indirizzi sono privati: ogni rotta
filtra sempre per l'utente autenticato, mai per il solo id, altrimenti
basterebbe cambiare il numero nell'URL per leggere dove abita un altro.

NB: NIENTE `from __future__ import annotations` (vedi api/orders.py).
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from helpers.auth import get_current_user
from models.db import ShippingAddress, User
from utils.session import get_db

LOGGER = logging.getLogger("addresses")

router = APIRouter(prefix="/api/addresses", tags=["addresses"])

# Un tetto basso ma piu' che sufficiente: serve a impedire che un account
# diventi un magazzino di righe, non a limitare un uso normale.
MAX_INDIRIZZI = 20


class AddressRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    street: str = Field(..., min_length=1, max_length=255)
    city: str = Field(..., min_length=1, max_length=120)
    postal_code: str = Field(..., min_length=1, max_length=20)
    province: Optional[str] = Field(None, max_length=120)
    country: str = Field("Italia", min_length=1, max_length=80)
    phone: Optional[str] = Field(None, max_length=50)
    label: Optional[str] = Field(None, max_length=60)
    is_default: bool = False


class AddressResponse(BaseModel):
    id: int
    label: Optional[str]
    full_name: str
    phone: Optional[str]
    street: str
    city: str
    postal_code: str
    province: Optional[str]
    country: str
    is_default: bool


def _to_response(a: ShippingAddress) -> AddressResponse:
    return AddressResponse(
        id=a.id,
        label=a.label,
        full_name=a.full_name,
        phone=a.phone,
        street=a.street,
        city=a.city,
        postal_code=a.postal_code,
        province=a.province,
        country=a.country,
        is_default=bool(a.is_default),
    )


def _solo_uno_predefinito(db: Session, user_id: int, vincitore_id: int) -> None:
    """Spegne il flag su tutti gli altri.

    Senza, due indirizzi predefiniti renderebbero imprevedibile quale
    viene proposto al checkout: dipenderebbe dall'ordine di lettura.
    """
    (
        db.query(ShippingAddress)
        .filter(
            ShippingAddress.user_id == user_id,
            ShippingAddress.id != vincitore_id,
        )
        .update({ShippingAddress.is_default: False}, synchronize_session=False)
    )


def _mio(db: Session, user: User, address_id: int) -> ShippingAddress:
    a = (
        db.query(ShippingAddress)
        .filter(
            ShippingAddress.id == address_id,
            ShippingAddress.user_id == user.id,
        )
        .first()
    )
    if a is None:
        # 404 anche quando l'indirizzo esiste ma e' di un altro: un 403
        # confermerebbe che quel numero corrisponde a qualcosa.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Indirizzo non trovato",
        )
    return a


@router.get("", response_model=List[AddressResponse])
def list_addresses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Predefinito in cima, poi i piu' recenti."""
    rows = (
        db.query(ShippingAddress)
        .filter(ShippingAddress.user_id == current_user.id)
        .order_by(
            ShippingAddress.is_default.desc(),
            ShippingAddress.id.desc(),
        )
        .all()
    )
    return [_to_response(a) for a in rows]


@router.post("", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
def create_address(
    payload: AddressRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quanti = (
        db.query(ShippingAddress)
        .filter(ShippingAddress.user_id == current_user.id)
        .count()
    )
    if quanti >= MAX_INDIRIZZI:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Hai raggiunto il massimo di {MAX_INDIRIZZI} indirizzi. "
                   "Cancellane uno per aggiungerne un altro.",
        )

    # Il primo diventa predefinito da solo: se non lo fosse, al checkout
    # successivo non ci sarebbe niente da precompilare.
    predefinito = payload.is_default or quanti == 0

    a = ShippingAddress(
        user_id=current_user.id,
        label=(payload.label or "").strip() or None,
        full_name=payload.full_name.strip(),
        phone=(payload.phone or "").strip() or None,
        street=payload.street.strip(),
        city=payload.city.strip(),
        postal_code=payload.postal_code.strip(),
        province=(payload.province or "").strip() or None,
        country=payload.country.strip(),
        is_default=predefinito,
    )
    db.add(a)
    db.flush()
    if predefinito:
        _solo_uno_predefinito(db, current_user.id, a.id)
    db.commit()
    db.refresh(a)
    return _to_response(a)


@router.put("/{address_id}", response_model=AddressResponse)
def update_address(
    address_id: int,
    payload: AddressRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    a = _mio(db, current_user, address_id)

    a.label = (payload.label or "").strip() or None
    a.full_name = payload.full_name.strip()
    a.phone = (payload.phone or "").strip() or None
    a.street = payload.street.strip()
    a.city = payload.city.strip()
    a.postal_code = payload.postal_code.strip()
    a.province = (payload.province or "").strip() or None
    a.country = payload.country.strip()

    # Togliere la spunta al predefinito senza darla a nessun altro
    # lascerebbe la rubrica senza proposta: la ignoriamo.
    if payload.is_default:
        a.is_default = True
        _solo_uno_predefinito(db, current_user.id, a.id)

    db.commit()
    db.refresh(a)
    return _to_response(a)


@router.post("/{address_id}/default", response_model=AddressResponse)
def set_default(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    a = _mio(db, current_user, address_id)
    a.is_default = True
    _solo_uno_predefinito(db, current_user.id, a.id)
    db.commit()
    db.refresh(a)
    return _to_response(a)


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    a = _mio(db, current_user, address_id)
    era_predefinito = bool(a.is_default)
    db.delete(a)
    db.flush()

    # Se se n'e' andato il predefinito, promuoviamo il piu' recente fra i
    # rimasti: una rubrica piena senza nessuna proposta non aiuterebbe
    # nessuno al checkout.
    if era_predefinito:
        erede = (
            db.query(ShippingAddress)
            .filter(ShippingAddress.user_id == current_user.id)
            .order_by(ShippingAddress.id.desc())
            .first()
        )
        if erede is not None:
            erede.is_default = True

    db.commit()
    return None
