#!/bin/bash
set -e

DB_FILE="${SQLITE_DB_PATH:-/app/data/nerdnostalgia.db}"
SCHEMA_FILE="/app/database/schema.sql"
MIGRATIONS_DIR="/app/database/migrations"

mkdir -p "$(dirname "$DB_FILE")"

if [ ! -f "$DB_FILE" ]; then
  echo "DB SQLite non trovato in $DB_FILE — creo schema iniziale."
fi

# schema.sql e' idempotente (IF NOT EXISTS), applicabile sempre.
sqlite3 "$DB_FILE" < "$SCHEMA_FILE"

# Migrazioni incrementali (tracking via tabella schema_migrations).
if [ -d "$MIGRATIONS_DIR" ]; then
  SQLITE_DB_PATH="$DB_FILE" MIGRATIONS_DIR="$MIGRATIONS_DIR" \
    python /app/scripts/run_migrations.py
fi

echo "SQLite pronto: $DB_FILE"
exec uvicorn src.main:app --host 0.0.0.0 --port 7373
