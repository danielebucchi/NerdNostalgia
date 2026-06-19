"""
Backup giornaliero di SQLite + cartella uploads.

Snapshot atomico del DB via API `.backup` di sqlite3 (consistente anche
con scritture in corso), seguito da tar.gz di /tmp/nerdnostalgia/uploads.
Prune: conserva gli ultimi BACKUP_RETENTION_DAYS giorni (default 30).

Se BACKUP_S3_BUCKET e' settato, fa anche upload su S3/R2 via boto3
(opzionale: se boto3 non e' installato, salta l'upload e logga).

Path di backup: /app/data/backups/  (gia' nel volume bind ./data)

Trigger: cron giornaliero alle 03:30 timezone applicazione.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import subprocess
import tarfile
from datetime import datetime, timedelta
from pathlib import Path

LOGGER = logging.getLogger("backup")

DB_PATH = Path(os.getenv("SQLITE_DB_PATH", "/app/data/nerdnostalgia.db"))
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "/app/data/backups"))
UPLOADS_DIR = Path(os.getenv("APP_TMP_DIR", "/tmp/nerdnostalgia")) / "uploads"
RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _sqlite_snapshot(src: Path, dst: Path) -> None:
    """Snapshot online consistente. SAFE anche con scritture concorrenti."""
    if not src.exists():
        raise FileNotFoundError(f"DB sorgente non trovato: {src}")
    src_conn = sqlite3.connect(str(src))
    dst_conn = sqlite3.connect(str(dst))
    try:
        with dst_conn:
            src_conn.backup(dst_conn)
    finally:
        src_conn.close()
        dst_conn.close()


def _tar_uploads(out_path: Path) -> bool:
    """Tar.gz della cartella uploads. Restituisce False se assente/vuota."""
    if not UPLOADS_DIR.exists() or not any(UPLOADS_DIR.iterdir()):
        return False
    with tarfile.open(out_path, "w:gz") as tar:
        tar.add(UPLOADS_DIR, arcname="uploads")
    return True


def _maybe_upload_s3(local_path: Path) -> None:
    bucket = os.getenv("BACKUP_S3_BUCKET")
    if not bucket:
        return
    try:
        import boto3  # type: ignore
    except ImportError:
        LOGGER.warning("BACKUP_S3_BUCKET settato ma boto3 non installato — skip upload")
        return

    endpoint = os.getenv("BACKUP_S3_ENDPOINT") or None
    region = os.getenv("AWS_DEFAULT_REGION", "auto")
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=region,
    )
    key = local_path.name
    try:
        s3.upload_file(str(local_path), bucket, key)
        LOGGER.info("Backup caricato su s3://%s/%s", bucket, key)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Upload S3 fallito: %s", exc)


def _prune_old() -> None:
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    for f in BACKUP_DIR.iterdir():
        try:
            if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                f.unlink()
                LOGGER.info("Backup vecchio rimosso: %s", f.name)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Prune fallito su %s: %s", f, exc)


def run_backup() -> None:
    """Eseguito dal cron job APScheduler."""
    _ensure_dir(BACKUP_DIR)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    db_out = BACKUP_DIR / f"nerdnostalgia-{timestamp}.db"
    LOGGER.info("Backup SQLite -> %s", db_out)
    try:
        _sqlite_snapshot(DB_PATH, db_out)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Snapshot DB fallito: %s", exc)
        return

    _maybe_upload_s3(db_out)

    uploads_out = BACKUP_DIR / f"uploads-{timestamp}.tar.gz"
    try:
        has_uploads = _tar_uploads(uploads_out)
        if has_uploads:
            LOGGER.info("Backup uploads -> %s", uploads_out)
            _maybe_upload_s3(uploads_out)
        else:
            LOGGER.info("Nessun upload da archiviare.")
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Tar uploads fallito: %s", exc)

    _prune_old()
