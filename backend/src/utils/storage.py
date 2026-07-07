"""
Gestione file uploads su filesystem.
"""
import io
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageOps, UnidentifiedImageError

APP_TMP_DIR = os.getenv("APP_TMP_DIR", "/tmp/nerdnostalgia")
UPLOADS_DIR = Path(APP_TMP_DIR) / "uploads"
ARTICLES_UPLOADS_DIR = UPLOADS_DIR / "articles"
INVENTORY_UPLOADS_DIR = UPLOADS_DIR / "inventory"

# Scope validi per il naming delle sottocartelle. Corrispondono anche al
# segmento di URL /static/<scope>/<id>/<uuid>.webp. Aggiungere qui una voce
# nuova basta a supportare un nuovo tipo di entita' con la stessa pipeline.
_SCOPES = {
    "articles": ARTICLES_UPLOADS_DIR,
    "inventory": INVENTORY_UPLOADS_DIR,
}

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

# Larghezze massime delle varianti generate (in px). Il file principale è
# sempre WebP ottimizzato. La variante "thumb" viene servita nelle card e
# riduce drasticamente la banda.
LARGE_MAX_WIDTH = 1600
THUMB_MAX_WIDTH = 600
WEBP_QUALITY = 82


class UploadValidationError(Exception):
    """Errore di validazione del file caricato."""


def ensure_dirs() -> None:
    for base in _SCOPES.values():
        base.mkdir(parents=True, exist_ok=True)


def article_dir(article_id: int) -> Path:
    return ARTICLES_UPLOADS_DIR / str(article_id)


def _scope_dir(scope: str, entity_id: int) -> Path:
    if scope not in _SCOPES:
        raise ValueError(f"scope invalido: {scope!r}")
    return _SCOPES[scope] / str(entity_id)


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


def _read_with_limit(file_obj) -> bytes:
    """Legge il contenuto applicando il limite massimo. Solleva validation error."""
    buffer = bytearray()
    while True:
        chunk = file_obj.read(64 * 1024)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > MAX_UPLOAD_SIZE_BYTES:
            raise UploadValidationError(
                f"File troppo grande (limite {MAX_UPLOAD_SIZE_MB} MB)"
            )
    return bytes(buffer)


def _resize_to_webp(image: Image.Image, max_width: int) -> bytes:
    """Ridimensiona mantenendo l'aspect ratio e ritorna i bytes WebP."""
    if image.width > max_width:
        ratio = max_width / float(image.width)
        new_size = (max_width, int(image.height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    out = io.BytesIO()
    image.save(out, format="WEBP", quality=WEBP_QUALITY, method=6)
    return out.getvalue()


def save_upload(
    scope: str,
    entity_id: int,
    file_obj,
    content_type: str,
) -> Tuple[str, Path]:
    """
    Salva un file immagine su disco generando due varianti WebP:
      - {uuid}.webp        → versione grande (max 1600px)
      - {uuid}.thumb.webp  → versione card (max 600px)

    `scope` identifica la sottocartella (articles, inventory, ...).

    Restituisce (public_url della versione grande, path_on_disk).
    Solleva UploadValidationError se content-type non ammesso o dimensione
    eccessiva.
    """
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise UploadValidationError(
            f"Content-type '{content_type}' non ammesso. "
            f"Ammessi: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
        )

    raw = _read_with_limit(file_obj)

    try:
        with Image.open(io.BytesIO(raw)) as img:
            # Rispetta orientamento EXIF e normalizza il mode (es. RGBA → RGB)
            img = ImageOps.exif_transpose(img)
            if img.mode in ("P", "RGBA"):
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")

            large_bytes = _resize_to_webp(img.copy(), LARGE_MAX_WIDTH)
            thumb_bytes = _resize_to_webp(img.copy(), THUMB_MAX_WIDTH)
    except UnidentifiedImageError as exc:
        raise UploadValidationError("File non riconosciuto come immagine valida") from exc

    uid = uuid.uuid4().hex
    dest_dir = _scope_dir(scope, entity_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    large_path = dest_dir / f"{uid}.webp"
    thumb_path = dest_dir / f"{uid}.thumb.webp"

    large_path.write_bytes(large_bytes)
    thumb_path.write_bytes(thumb_bytes)

    relative = f"{scope}/{entity_id}/{large_path.name}"
    return public_url(relative), large_path


def save_article_image(
    article_id: int,
    file_obj,
    content_type: str,
) -> Tuple[str, Path]:
    """Wrapper storico per backward-compat: delega a save_upload(articles)."""
    return save_upload("articles", article_id, file_obj, content_type)


def save_inventory_image(
    item_id: int,
    file_obj,
    content_type: str,
) -> Tuple[str, Path]:
    """Salva un'immagine legata a un inventory_item del lotto."""
    return save_upload("inventory", item_id, file_obj, content_type)


def thumb_url_for(url: str) -> str:
    """Ritorna l'URL del thumbnail .thumb.webp se l'URL è una nostra immagine
    grande .webp, altrimenti ritorna l'URL originale invariato (compatibilità
    con immagini esterne o file caricati prima dell'introduzione dei thumb)."""
    if not is_internal_url(url):
        return url
    if url.endswith(".webp") and not url.endswith(".thumb.webp"):
        return url[: -len(".webp")] + ".thumb.webp"
    return url


def delete_file_for_url(url: str) -> bool:
    """Cancella il file su disco corrispondente a un URL interno e il
    thumbnail associato. Ritorna True se almeno un file è stato rimosso."""
    path = path_from_internal_url(url)
    removed = False
    if path is not None and path.exists():
        try:
            path.unlink()
            removed = True
        except OSError:
            pass

    # Best-effort: rimuove anche il .thumb.webp gemello
    if path is not None and path.name.endswith(".webp") and not path.name.endswith(".thumb.webp"):
        thumb_path = path.with_name(path.stem + ".thumb.webp")
        if thumb_path.exists():
            try:
                thumb_path.unlink()
                removed = True
            except OSError:
                pass

    return removed


def delete_upload_dir(scope: str, entity_id: int) -> None:
    """Cancella tutta la cartella uploads di un'entita' (best effort)."""
    try:
        target = _scope_dir(scope, entity_id)
    except ValueError:
        return
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)


def delete_article_dir(article_id: int) -> None:
    """Wrapper storico per backward-compat."""
    delete_upload_dir("articles", article_id)


def delete_inventory_dir(item_id: int) -> None:
    delete_upload_dir("inventory", item_id)
