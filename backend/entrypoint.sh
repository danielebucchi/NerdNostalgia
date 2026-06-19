#!/bin/bash
set -e

DB_FILE="${SQLITE_DB_PATH:-/app/data/nerdnostalgia.db}"
SCHEMA_FILE="/app/database/schema.sql"

mkdir -p "$(dirname "$DB_FILE")"

if [ ! -f "$DB_FILE" ]; then
  echo "DB SQLite non trovato in $DB_FILE — creo schema iniziale."
  sqlite3 "$DB_FILE" < "$SCHEMA_FILE"
else
  # Applica schema (idempotente grazie a IF NOT EXISTS) — utile dopo nuove tabelle
  sqlite3 "$DB_FILE" < "$SCHEMA_FILE"
fi

echo "SQLite pronto: $DB_FILE"
exec uvicorn src.main:app --host 0.0.0.0 --port 7373
