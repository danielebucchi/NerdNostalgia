import datetime
from datetime import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from helpers.auth import require_admin
from helpers.user import get_user_helper, UserHelper
from models.db import User
from models.entities.user import UserResponse, UserCreate, UserUpdate
from utils.security import hash_password
from utils.session import get_db

router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    user_helper: UserHelper = Depends(get_user_helper),
    _admin: User = Depends(require_admin),
):
    """Crea un nuovo utente. ADMIN-ONLY.

    Per il primissimo bootstrap dell'admin usa la migrazione 0001_seed
    (crea 'admin'/'changeme') oppure lo script `scripts/create_admin.py`
    che gira direttamente dentro il container, senza passare per l'API.
    """
    # Check if username already exists
    existing_user = user_helper.get("username", user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user_data.username}' gia' registrato"
        )

    # Check if email already exists
    existing_email = user_helper.get("email", user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{user_data.email}' gia' registrata"
        )

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
    )
    user_helper.save(new_user)



    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        is_active=new_user.is_active,
        is_verified=new_user.is_verified,
        created_at=new_user.created_at.isoformat(),
        updated_at=new_user.updated_at.isoformat(),
    )


@router.get("/", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    user_helper: UserHelper = Depends(get_user_helper),
    _admin: User = Depends(require_admin),
):
    """
    Lista tutti gli utenti con paginazione e filtri.

    Args:
        skip: Numero di record da saltare
        limit: Numero massimo di record
        is_active: Filtra per utenti attivi/inattivi
        user_helper: Helper per l'utente

    Returns:
        List[UserResponse]: Lista di utenti
    """
    users = user_helper.gets(is_active=is_active, skip=skip, limit=limit)

    return [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        )
        for user in users
    ]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    user_helper: UserHelper = Depends(get_user_helper),
    _admin: User = Depends(require_admin),
):
    """
    Ottieni un utente per ID.

    Args:
        user_id: ID dell'utente
        user_helper: Helper per l'utente

    Returns:
        UserResponse: Utente trovato

    Raises:
        HTTPException: Se utente non trovato
    """
    user = user_helper.get("id", user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Utente con ID {user_id} non trovato"
        )

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: int,
                user_data: UserUpdate,
                user_helper: UserHelper = Depends(get_user_helper),
                _admin: User = Depends(require_admin)):
    """
    Aggiorna un utente.

    Args:
        user_id: ID dell'utente
        user_data: Dati da aggiornare
        user_helper: Helper per l'utente

    Returns:
        UserResponse: Utente aggiornato

    Raises:
        HTTPException: Se utente non trovato
    """
    user = user_helper.get("id", user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Utente con ID {user_id} non trovato"
        )

    user_helper.update(user_data, user)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int,
                user_helper: UserHelper = Depends(get_user_helper),
                _admin: User = Depends(require_admin)):
    """
    Elimina un utente.

    Args:
        user_id: ID dell'utente da eliminare
        user_helper: Helper per l'utente

    Raises:
        HTTPException: Se utente non trovato
    """
    user = user_helper.get("id", user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Utente con ID {user_id} non trovato"
        )

    user_helper.delete(user)

    return None


@router.get("/username/{username}", response_model=UserResponse)
def get_user_by_username(username: str,
                user_helper: UserHelper = Depends(get_user_helper),
                _admin: User = Depends(require_admin)):
    """
    Ottieni un utente per username.

    Args:
        username: Username dell'utente
        user_helper: Helper per l'utente

    Returns:
        UserResponse: Utente trovato

    Raises:
        HTTPException: Se utente non trovato
    """
    user=user_helper.get("username", username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Utente '{username}' non trovato"
        )

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )
