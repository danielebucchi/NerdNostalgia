"""
Fixture comuni per i test backend.

Approccio:
- Engine SQLAlchemy in-memory per test, isolato da `data/nerdnostalgia.db`.
- Schema.sql applicato all'engine all'avvio della sessione test.
- Override della dependency get_db con la sessione test.
- TestClient FastAPI riusabile.
- Admin user seedato a inizio test, JWT pronto in `admin_headers`.
- Rate limiter resettato fra test (slowapi e' globale per IP).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# I moduli backend usano import "flat" (es. `from utils.session import ...`)
# perche' in prod PYTHONPATH=/app/src. Riproduco lo stesso qui.
ROOT = Path(__file__).resolve().parents[1]  # backend/
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

# Env coerenti coi test (JWT secret deterministica, niente email, niente cron)
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("EMAIL_ENABLED", "0")
os.environ.setdefault("DISABLE_SCHEDULER", "1")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from main import app  # noqa: E402
from models.db import User, UserRole  # noqa: E402
from utils.limiter import limiter  # noqa: E402
from utils.security import create_access_token, hash_password  # noqa: E402
from utils.session import get_db  # noqa: E402


def _find_schema() -> Path:
    """schema.sql vive in:
    - container: /app/database/schema.sql (mountato via compose)
    - dev locale: <repo>/database/schema.sql (sibling di backend/)
    """
    candidates = [
        ROOT / "database" / "schema.sql",        # /app/database/...
        ROOT.parent / "database" / "schema.sql", # <repo>/database/...
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(f"schema.sql non trovato in {candidates}")


SCHEMA_PATH = _find_schema()


@pytest.fixture()
def engine():
    """Engine SQLite in-memory **per-test**, con StaticPool per condividere la
    stessa connection fra request del TestClient (altrimenti `:memory:` perde
    i dati tra connection diverse). DB nuovo a ogni test → isolamento totale."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    @event.listens_for(eng, "connect")
    def _fk_pragma(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    # Applica schema (idempotente con IF NOT EXISTS).
    # executescript() del cursor sqlite3 gestisce nativamente i multi-statement
    # e ignora i ';' dentro commenti — il naive split(';') si rompeva
    # in mezzo a commenti che contenevano un ';'.
    with eng.connect() as conn:
        with open(SCHEMA_PATH) as f:
            sql = f.read()
        raw_conn = conn.connection.driver_connection  # sqlite3.Connection
        raw_conn.executescript(sql)
        conn.commit()

    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(engine):
    """Sessione SQLAlchemy legata all'engine per-test."""
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    """TestClient con get_db override e rate limiter pulito."""
    def _get_db_override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db_override
    limiter.reset()

    with TestClient(app, base_url="http://testserver") as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def admin_user(db_session):
    user = User(
        username="admin",
        email="admin@test.local",
        hashed_password=hash_password("admin123"),
        full_name="Test Admin",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def admin_token(admin_user):
    return create_access_token(subject=admin_user.username, role=admin_user.role.value)


@pytest.fixture()
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture()
def auth_client(client, admin_headers):
    """TestClient con header Authorization admin gia' settato."""
    client.headers.update(admin_headers)
    return client
