"""Unit: schema.sql deve applicarsi anche a un DB che le migrazioni non hanno
ancora aggiornato.

L'entrypoint esegue schema.sql prima delle migrazioni. Una CREATE INDEX in
schema.sql su una colonna che arriva con ALTER TABLE ... ADD COLUMN in una
migrazione fallisce sul DB di produzione (la tabella esiste gia', senza la
colonna) e il backend resta in crash loop: l'indice va nella migrazione.
"""
import re
from pathlib import Path

DATABASE = Path(__file__).resolve().parents[3] / "database"

_ADD_COLUMN = re.compile(
    r"ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(\w+)", re.IGNORECASE
)
_CREATE_INDEX = re.compile(
    r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s+ON\s+(\w+)\s*\(([^)]*)\)",
    re.IGNORECASE,
)


def _migrated_columns() -> dict:
    added = {}
    for path in sorted((DATABASE / "migrations").glob("*.sql")):
        for table, column in _ADD_COLUMN.findall(path.read_text()):
            added.setdefault((table.lower(), column.lower()), path.name)
    return added


def test_schema_indexes_do_not_use_migrated_columns():
    added = _migrated_columns()
    offending = []
    for name, table, cols in _CREATE_INDEX.findall((DATABASE / "schema.sql").read_text()):
        for col in re.findall(r"\w+", cols):
            key = (table.lower(), col.lower())
            if key in added and col.upper() not in ("ASC", "DESC"):
                offending.append(f"{name}: {table}.{col} (aggiunta da {added[key]})")
    assert not offending, (
        "Indici in schema.sql su colonne aggiunte da migrazioni: spostali in una "
        "migrazione.\n" + "\n".join(offending)
    )
