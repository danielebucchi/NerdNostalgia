"""
Gestione file uploads su filesystem.
"""
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, Tuple

APP_TMP_DIR = os.getenv("APP_TMP_DIR", "/tmp/nerdnostalgia")
UPLOADS_DIR = Path(APP_TMP_DIR) / "uploads"
ARTICLES_UPLOADS_DIR = UPLOADS_DIR / "articles"

BASE_URL = os.getenv("BASE_URL", "http://localhost:7373")
STATIC_URL_PREFIX = "/static"

MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "5"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


class UploadValidationError(Exception):
    """Errore di validazione del file caricato."""


def ensure_dirs() -> None:
    ARTICLES_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def article_dir(article_id: int) -> Path:
    return ARTICLES_UPLOADS_DIR / str(article_id)


def public_url(relative_path: str) -> str:
    """Costruisce l'URL pubblico per una path relativa a uploads/."""
    return f"{BASE_URL}{STATIC_URL_PREFIX}/{relative_path.lstrip('/')}"


def is_internal_url(url: str) -> bool:
    """True se l'URL e' servito dal nostro storage statico."""
    prefix = f"{BASE_URL}{STATIC_URL_PREFIX}/"
    return url.startswith(prefix)


def path_from_internal_url(url: str) -> Optional[Path]:
    """Risolve un URL interno alla sua path su disco. None se non e' interno."""
    if not is_internal_url(url):
        return None
    prefix = f"{BASE_URL}{STATIC_URL_PREFIX}/"
    relative = url[len(prefix):]
    candidate = (UPLOADS_DIR / relative).resolve()
    try:
        candidate.relative_to(UPLOADS_DIR.resolve())
    except ValueError:
        return None
    return candidate


def save_article_image(
    article_id: int,
    file_obj,
    content_type: str,
) -> Tuple[str, Path]:
    """
    Salva un file immagine su disco e restituisce (public_url, path_on_disk).

    Solleva UploadValidationError se content-type non ammesso o dimensione
    eccessiva.
    """
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise UploadValidationError(
            f"Content-type '{content_type}' non ammesso. "
            f"Ammessi: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
        )

    extension = ALLOWED_CONTENT_TYPES[content_type]
    filename = f"{uuid.uuid4().hex}.{extension}"

    dest_dir = article_dir(article_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename

    written = 0
    with dest_path.open("wb") as out:
        while True:
            chunk = file_obj.read(64 * 1024)
            if not chunk:
                break
            written += len(chunk)
            if written > MAX_UPLOAD_SIZE_BYTES:
                out.close()
                dest_path.unlink(missing_ok=True)
                raise UploadValidationError(
                    f"File troppo grande (limite {MAX_UPLOAD_SIZE_MB} MB)"
                )
            out.write(chunk)

    relative = f"articles/{article_id}/{filename}"
    return public_url(relative), dest_path


def delete_file_for_url(url: str) -> bool:
    """Cancella il file su disco corrispondente a un URL interno. Ritorna True se cancellato."""
    path = path_from_internal_url(url)
    if path is None or not path.exists():
        return False
    try:
        path.unlink()
        return True
    except OSError:
        return False


def delete_article_dir(article_id: int) -> None:
    """Cancella tutta la cartella uploads di un articolo (best effort)."""
    target = article_dir(article_id)
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
