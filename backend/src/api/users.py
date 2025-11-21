import datetime
from datetime import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from models.db import User
from models.entities.user import UserResponse, UserCreate, UserUpdate
from utils.session import get_db

router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Crea un nuovo utente.

    Args:
        user_data: Dati del nuovo utente
        db: Sessione database

    Returns:
        UserResponse: Utente creato

    Raises:
        HTTPException: Se username o email gia' esistono
    """
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user_data.username}' gia' registrato"
        )

    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{user_data.email}' gia' registrata"
        )

    # Create user (TODO: hash password with bcrypt!)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=user_data.password,  # TODO: Hash this in production!
        full_name=user_data.full_name,
        role=user_data.role,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

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
    db: Session = Depends(get_db)
):
    """
    Lista tutti gli utenti con paginazione e filtri.

    Args:
        skip: Numero di record da saltare
        limit: Numero massimo di record
        is_active: Filtra per utenti attivi/inattivi
        db: Sessione database

    Returns:
        List[UserResponse]: Lista di utenti
    """
    query = db.query(User)

    # Apply filters
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    users = query.offset(skip).limit(limit).all()

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
def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    Ottieni un utente per ID.

    Args:
        user_id: ID dell'utente
        db: Sessione database

    Returns:
        UserResponse: Utente trovato

    Raises:
        HTTPException: Se utente non trovato
    """
    user = db.query(User).filter(User.id == user_id).first()
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
def update_user(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db)):
    """
    Aggiorna un utente.

    Args:
        user_id: ID dell'utente
        user_data: Dati da aggiornare
        db: Sessione database

    Returns:
        UserResponse: Utente aggiornato

    Raises:
        HTTPException: Se utente non trovato
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Utente con ID {user_id} non trovato"
        )

    update_data = user_data.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(user, key, value)

    user.updated_at = dt.now(datetime.UTC)

    db.commit()
    db.refresh(user)

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
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """
    Elimina un utente.

    Args:
        user_id: ID dell'utente da eliminare
        db: Sessione database

    Raises:
        HTTPException: Se utente non trovato
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Utente con ID {user_id} non trovato"
        )

    db.delete(user)
    db.commit()
    return None


@router.get("/username/{username}", response_model=UserResponse)
def get_user_by_username(username: str, db: Session = Depends(get_db)):
    """
    Ottieni un utente per username.

    Args:
        username: Username dell'utente
        db: Sessione database

    Returns:
        UserResponse: Utente trovato

    Raises:
        HTTPException: Se utente non trovato
    """
    user = db.query(User).filter(User.username == username).first()
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
