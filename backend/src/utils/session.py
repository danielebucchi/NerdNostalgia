"""
Database session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os

# Database URL from environment (default: SQLite locale)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/nerdnostalgia.db")

# Per SQLite serve check_same_thread=False con FastAPI (più thread per request)
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
    connect_args=_connect_args,
)

# Abilita foreign keys su SQLite (per default sono OFF)
if DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _fk_pragma_on_connect(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

# Create SessionLocal class
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency per ottenere una sessione database.

    Yields:
        Session: Sessione database SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
