"""
Migrazione dati PostgreSQL -> SQLite (one-shot).

Si connette a:
- Postgres tramite DATABASE_URL_PG (env)
- SQLite tramite path file (env SQLITE_PATH, default ./data/nerdnostalgia.db)

Per ogni tabella copia i record 1:1. Le colonne JSON/JSONB vengono
trasformate in stringhe JSON. Le date/timestamp restano string in SQLite.
Boolean diventano 0/1.

Uso:
    DATABASE_URL_PG="postgresql://user:password@localhost:5433/nerdnostalgia" \\
    SQLITE_PATH="./data/nerdnostalgia.db" \\
    python scripts/migrate_pg_to_sqlite.py

Lo script presuppone che schema.sql sia stato gia' applicato sul DB SQLite.
"""
import json
import os
import sqlite3
import sys
from datetime import date, datetime
from decimal import Decimal

import psycopg2
import psycopg2.extras

# Ordine importante: prima le tabelle senza FK, poi quelle che dipendono.
TABLES = [
    "users",
    "categories",
    "articles",
    "inquiries",
    "wanted_items",
    "card_purchases",
    "misc_sales",
    "marketplace_fees",
    "vinted_settings",
    "vinted_sync_logs",
    "lots",
    "inventory_items",
    "personal_cards",
    "expenses",
    "platforms",
    "consignment_sales",
]

# Per ogni tabella, le colonne JSON/JSONB da serializzare
JSON_COLUMNS = {
    "articles": ["images", "article_metadata"],
    "inventory_items": ["images"],
    "personal_cards": ["images"],
}

# Boolean columns per tabella (li convertiamo 0/1 esplicitamente)
BOOL_COLUMNS = {
    "users": ["is_active", "is_verified"],
    "platforms": ["is_active"],
    "vinted_settings": ["enabled"],
    "misc_sales": ["paid_by_buyer"],
    "expenses": ["related_to_cards", "related_to_creations"],
    "consignment_sales": ["paid_out"],
}


def convert(value, col_name, table):
    if value is None:
        return None
    if col_name in JSON_COLUMNS.get(table, []):
        # PG ritorna gia' dict/list per JSONB; serializziamo.
        return json.dumps(value, ensure_ascii=False, default=str)
    if col_name in BOOL_COLUMNS.get(table, []):
        return 1 if value else 0
    if isinstance(value, Decimal):
        # Mantengo come stringa per non perdere precisione (SQLite NUMERIC e' flexible)
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def copy_table(pg_cur, sq_conn, table):
    pg_cur.execute(f"SELECT * FROM {table}")
    rows = pg_cur.fetchall()
    if not rows:
        print(f"  {table}: 0 righe (skip)")
        return

    col_names = [d[0] for d in pg_cur.description]
    placeholders = ",".join(["?"] * len(col_names))
    columns_sql = ",".join(col_names)
    insert_sql = f"INSERT INTO {table} ({columns_sql}) VALUES ({placeholders})"

    converted = []
    for row in rows:
        converted.append(tuple(convert(row[c], c, table) for c in col_names))

    sq_cur = sq_conn.cursor()
    sq_cur.execute(f"DELETE FROM {table}")  # idempotenza
    sq_cur.executemany(insert_sql, converted)
    sq_conn.commit()
    print(f"  {table}: {len(rows)} righe migrate")


def apply_schema(sqlite_path, schema_path):
    """Crea il file SQLite (se manca) e applica lo schema."""
    os.makedirs(os.path.dirname(sqlite_path) or ".", exist_ok=True)
    with open(schema_path) as f:
        sql = f.read()
    conn = sqlite3.connect(sqlite_path)
    conn.executescript(sql)
    conn.commit()
    conn.close()
    print(f"Schema applicato su {sqlite_path}")


def main():
    pg_url = os.getenv(
        "DATABASE_URL_PG",
        "postgresql://user:password@localhost:5433/nerdnostalgia",
    )
    sqlite_path = os.getenv("SQLITE_PATH", "./data/nerdnostalgia.db")
    schema_path = os.getenv("SCHEMA_PATH", "./database/schema.sql")

    if not os.path.exists(sqlite_path):
        if not os.path.exists(schema_path):
            sys.exit(f"Né DB SQLite né schema trovati ({sqlite_path}, {schema_path}).")
        apply_schema(sqlite_path, schema_path)

    print(f"PG  -> {pg_url}")
    print(f"SQL -> {sqlite_path}")
    print()

    pg_conn = psycopg2.connect(pg_url)
    pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    sq_conn = sqlite3.connect(sqlite_path)
    sq_conn.execute("PRAGMA foreign_keys = OFF")  # spegniamo FK durante import

    try:
        for t in TABLES:
            copy_table(pg_cur, sq_conn, t)
    finally:
        sq_conn.execute("PRAGMA foreign_keys = ON")
        sq_conn.close()
        pg_cur.close()
        pg_conn.close()

    print()
    print("Migrazione completata.")


if __name__ == "__main__":
    main()
