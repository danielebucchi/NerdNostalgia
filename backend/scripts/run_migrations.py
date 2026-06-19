"""
Migration runner per SQLite.

Applica i file .sql in /app/database/migrations/ in ordine alfanumerico,
tenendo traccia delle migrazioni gia' applicate nella tabella
schema_migrations.

Idempotente: rieseguibile a ogni avvio del container.

Env vars:
  SQLITE_DB_PATH   path del file SQLite (default /app/data/nerdnostalgia.db)
  MIGRATIONS_DIR   directory dei .sql (default /app/database/migrations)
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def applied_versions(conn: sqlite3.Connection) -> set[str]:
    cur = conn.execute("SELECT version FROM schema_migrations")
    return {row[0] for row in cur.fetchall()}


def apply_migration(conn: sqlite3.Connection, path: Path) -> None:
    version = path.stem  # nome senza .sql
    sql = path.read_text()
    print(f"  → applico {version}", flush=True)
    conn.executescript(sql)
    conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
    conn.commit()


def main() -> int:
    db_path = os.getenv("SQLITE_DB_PATH", "/app/data/nerdnostalgia.db")
    mig_dir = Path(os.getenv("MIGRATIONS_DIR", "/app/database/migrations"))

    if not os.path.exists(db_path):
        print(f"DB non trovato in {db_path}, salto migrazioni (verra' creato da schema.sql).")
        return 0
    if not mig_dir.is_dir():
        print(f"Directory migrazioni assente ({mig_dir}), niente da fare.")
        return 0

    sql_files = sorted(p for p in mig_dir.glob("*.sql") if p.is_file())
    if not sql_files:
        print("Nessuna migrazione presente.")
        return 0

    conn = sqlite3.connect(db_path)
    try:
        ensure_table(conn)
        already = applied_versions(conn)
        pending = [p for p in sql_files if p.stem not in already]

        if not pending:
            print(f"Migrazioni allineate ({len(already)} gia' applicate).")
            return 0

        print(f"Applico {len(pending)} migrazioni pending:")
        for p in pending:
            try:
                apply_migration(conn, p)
            except Exception as exc:  # noqa: BLE001
                print(f"  ✗ ERRORE su {p.name}: {exc}", file=sys.stderr)
                return 1
        print("Migrazioni completate.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
