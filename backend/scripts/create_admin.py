"""
CLI per creare/aggiornare un utente admin direttamente sul DB.
Bypassa l'API (che richiede gia' un admin per creare altri admin).

Usi tipici (da host):
  docker exec -it nerdnostalgia-backend python /app/scripts/create_admin.py \\
    --username daniele --email daniele@example.com

  # prompt password interattivo se manca --password
  # idempotente con --update: se username esiste, aggiorna password/email/role

Argomenti:
  --username    obbligatorio
  --email       obbligatorio
  --password    se omesso, viene richiesto interattivamente (getpass)
  --full-name   opzionale
  --role        ADMIN (default) | USER | GUEST
  --update      se l'utente esiste gia', aggiorna i campi invece di fallire
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

# Permetti import "flat" come in prod
SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from models.db import User, UserRole  # noqa: E402
from utils.security import hash_password  # noqa: E402
from utils.session import SessionLocal  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Crea/aggiorna un utente admin")
    p.add_argument("--username", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--password", help="Se omesso, prompt interattivo.")
    p.add_argument("--full-name", dest="full_name", default=None)
    p.add_argument(
        "--role",
        choices=[r.value for r in UserRole],
        default=UserRole.ADMIN.value,
    )
    p.add_argument(
        "--update",
        action="store_true",
        help="Se username esiste, aggiorna invece di fallire.",
    )
    return p.parse_args()


def _read_password() -> str:
    pw = getpass.getpass("Password: ")
    if not pw:
        print("Password vuota, abort.", file=sys.stderr)
        sys.exit(2)
    pw2 = getpass.getpass("Ripeti: ")
    if pw != pw2:
        print("Le password non coincidono.", file=sys.stderr)
        sys.exit(2)
    return pw


def main() -> int:
    args = parse_args()

    password = args.password or _read_password()
    if len(password) < 6:
        print("Password troppo corta (min 6 char).", file=sys.stderr)
        return 2

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == args.username).first()
        if existing and not args.update:
            print(
                f"Utente '{args.username}' esiste gia'. Usa --update per aggiornare.",
                file=sys.stderr,
            )
            return 1

        role = UserRole(args.role)

        if existing:
            existing.email = args.email
            existing.hashed_password = hash_password(password)
            existing.full_name = args.full_name or existing.full_name
            existing.role = role
            existing.is_active = True
            db.commit()
            db.refresh(existing)
            print(f"✓ Aggiornato utente id={existing.id} username={existing.username} role={role.value}")
            return 0

        user = User(
            username=args.username,
            email=args.email,
            hashed_password=hash_password(password),
            full_name=args.full_name,
            role=role,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"✓ Creato utente id={user.id} username={user.username} role={role.value}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
