"""
Modello User per SQLAlchemy.
"""
from sqlalchemy import Column, String, Boolean
import enum
from sqlalchemy import Enum as PgEnum
from .base import BaseModel


class UserRole(enum.Enum):
    """Ruoli utente."""
    ADMIN = "ADMIN"
    USER = "USER"
    GUEST = "GUEST"


class User(BaseModel):
    """
    Modello utente del sistema.

    Attributes:
        username: Username univoco dell'utente
        email: Email univoca dell'utente
        full_name: Nome completo
        hashed_password: Password hashata
        role: Ruolo dell'utente (ADMIN, USER, GUEST)
        is_active: Se l'utente e' attivo
        is_verified: Se l'email e' verificata
    """
    __tablename__ = "users"

    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    full_name = Column(String(255))

    role = Column(
        PgEnum(UserRole, name="user_role", create_type=False),
        nullable=False,
        default=UserRole.USER
    )

    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

    def to_dict(self, include_password=False):
        """
        Converte l'utente in dizionario.

        Args:
            include_password: Se includere l'hash della password (default: False)

        Returns:
            dict: Dizionario con i dati dell'utente
        """
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.value if self.role else None,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_password:
            data["hashed_password"] = self.hashed_password

        return data
