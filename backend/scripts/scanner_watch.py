#!/usr/bin/env python3
"""
Cartella osservata per lo scanner carte (gira sul Mac, non sul server).

Lo scanner salva gli scan in una cartella; questo script la tiene
d'occhio e manda ogni file nuovo a /api/card-scanner/scans, dove viene
riconosciuto e finisce nella coda "Da confermare" della pagina Scanner
carte. Gioco ed espansione sono quelli scelti nella pagina.

Un browser non puo' parlare con uno scanner; la cartella si', con
qualunque scanner: basta impostare il suo software (Acquisizione
Immagine, Epson ScanSmart, Canon IJ Scan Utility, ...) perche' salvi li'.

    python3 scanner_watch.py [cartella]          # default ~/Scansioni-carte

Credenziali come sync_from_local.py, da env o da
~/.config/nerdnostalgia/sync.env:
    NERDNOSTALGIA_API_URL   es. https://admin.nerdnostalgia.store o http://localhost:7373
    NERDNOSTALGIA_USERNAME
    NERDNOSTALGIA_PASSWORD
(NERDNOSTALGIA_API_URL si puo' sovrascrivere con --api, es. per provare in locale.)

Cosa succede ai file:
- caricato  → spostato in <cartella>/caricati/
- rifiutato → spostato in <cartella>/errori/ (con un .txt accanto che dice perche')
- il retro ("carta12_retro.jpg") va con il fronte dello stesso nome; se il
  fronte non e' ancora arrivato aspetta, e riprova al giro dopo.

Niente dipendenze: solo libreria standard + `sips` di macOS per ridurre gli
scan grossi (e convertire TIFF/HEIC in JPEG) prima di mandarli.
"""
import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Dict, Optional

LOGGER = logging.getLogger("scanner_watch")

ESTENSIONI = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic", ".bmp"}
LATO_MAX = 2400  # come il browser: basta e avanza per leggere il numero
INTERVALLO = 2.0
RE_RETRO = re.compile(r"^(.*?)[\s_-]*(retro|back)$", re.I)


# ── Configurazione ───────────────────────────────────────────────

def carica_env_file(path: Path) -> None:
    """KEY=VALUE per riga, come sync.env. Le variabili gia' presenti
    nell'ambiente vincono."""
    if not path.exists():
        return
    for riga in path.read_text().splitlines():
        riga = riga.strip()
        if not riga or riga.startswith("#") or "=" not in riga:
            continue
        k, v = riga.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# ── API ──────────────────────────────────────────────────────────

class Api:
    def __init__(self, base: str, username: str, password: str):
        self.base = base.rstrip("/")
        self.username = username
        self.password = password
        self.token: Optional[str] = None

    def login(self) -> None:
        data = urllib.parse.urlencode({"username": self.username, "password": self.password}).encode()
        with urllib.request.urlopen(f"{self.base}/api/auth/login", data=data, timeout=30) as r:
            self.token = json.load(r)["access_token"]

    def _richiesta(self, metodo: str, path: str, body: Optional[bytes] = None,
                   content_type: Optional[str] = None, timeout: int = 120):
        """Rifa il login una volta se il token e' scaduto (dura poco, e lo
        script resta acceso per ore)."""
        for tentativo in (1, 2):
            if not self.token:
                self.login()
            req = urllib.request.Request(f"{self.base}{path}", data=body, method=metodo)
            req.add_header("Authorization", f"Bearer {self.token}")
            if content_type:
                req.add_header("Content-Type", content_type)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return json.load(r)
            except urllib.error.HTTPError as exc:
                if exc.code == 401 and tentativo == 1:
                    self.token = None
                    continue
                dettaglio = exc.read().decode("utf-8", "ignore")[:300]
                try:
                    dettaglio = json.loads(dettaglio).get("detail", dettaglio)
                except ValueError:
                    pass
                raise RuntimeError(f"HTTP {exc.code}: {dettaglio}") from exc
        raise RuntimeError("login non riuscito")

    def invia_file(self, path: str, nome: str, file_path: Path) -> dict:
        confine = uuid.uuid4().hex
        corpo = (
            f"--{confine}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{nome}"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n"
        ).encode() + file_path.read_bytes() + f"\r\n--{confine}--\r\n".encode()
        return self._richiesta("POST", path, corpo, f"multipart/form-data; boundary={confine}")

    def scan_in_attesa(self) -> list:
        return self._richiesta("GET", "/api/card-scanner/scans?status=PENDING")


# ── File ─────────────────────────────────────────────────────────

def pronto(f: Path, dimensioni: Dict[Path, int]) -> bool:
    """Lo scanner scrive il file un pezzo alla volta: lo si prende solo
    quando la dimensione e' rimasta ferma per un giro."""
    try:
        ora = f.stat().st_size
    except FileNotFoundError:
        return False
    prima = dimensioni.get(f)
    dimensioni[f] = ora
    return ora > 0 and prima == ora


def riduci(f: Path, tmp: Path) -> Path:
    """JPEG con il lato lungo a LATO_MAX px. Il server accetta al massimo
    pochi MB, e uno scan a 600 dpi in PNG/TIFF ne pesa decine."""
    out = tmp / (f.stem + ".jpg")
    res = subprocess.run(
        ["sips", "-Z", str(LATO_MAX), "-s", "format", "jpeg", "-s", "formatOptions", "92",
         str(f), "--out", str(out)],
        capture_output=True,
    )
    if res.returncode != 0 or not out.exists():
        raise RuntimeError(f"conversione fallita: {res.stderr.decode('utf-8', 'ignore')[:200]}")
    return out


def sposta(f: Path, dest: Path, motivo: Optional[str] = None) -> None:
    dest.mkdir(exist_ok=True)
    finale = dest / f.name
    if finale.exists():  # stesso nome gia' passato: non sovrascrivere
        finale = dest / f"{f.stem}-{int(time.time())}{f.suffix}"
    shutil.move(str(f), finale)
    if motivo:
        finale.with_suffix(finale.suffix + ".txt").write_text(motivo + "\n")


def nome_fronte(f: Path) -> Optional[str]:
    m = RE_RETRO.match(f.stem)
    return m.group(1) if m else None


# ── Giro ─────────────────────────────────────────────────────────

def giro(cartella: Path, api: Api, dimensioni: Dict[Path, int], fronti: Dict[str, int]) -> None:
    candidati = sorted(
        (f for f in cartella.iterdir()
         if f.is_file() and f.suffix.lower() in ESTENSIONI and not f.name.startswith(".")),
        key=lambda f: f.stat().st_mtime,
    )
    # Prima i fronti, poi i retro: un retro ha bisogno del suo fronte.
    candidati.sort(key=lambda f: nome_fronte(f) is not None)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for f in candidati:
            if not pronto(f, dimensioni):
                continue
            base_fronte = nome_fronte(f)
            try:
                if base_fronte is None:
                    scan = api.invia_file("/api/card-scanner/scans", f.stem + ".jpg", riduci(f, tmp))
                    fronti[f.stem] = scan["id"]
                    primo = (scan.get("candidates") or [{}])[0]
                    LOGGER.info("%s → %s %s (%s)", f.name, primo.get("name", "?"),
                                primo.get("number", ""), scan.get("confidence"))
                else:
                    scan_id = fronti.get(base_fronte)
                    if scan_id is None:
                        # Fronte caricato in una sessione precedente?
                        for s in api.scan_in_attesa():
                            if Path(s.get("original_filename") or "").stem == base_fronte:
                                scan_id = fronti[base_fronte] = s["id"]
                                break
                    if scan_id is None:
                        continue  # il fronte non e' ancora arrivato: si riprova dopo
                    api.invia_file(f"/api/card-scanner/scans/{scan_id}/back", f.stem + ".jpg", riduci(f, tmp))
                    LOGGER.info("%s → retro dello scan %s", f.name, scan_id)
                sposta(f, cartella / "caricati")
            except (RuntimeError, urllib.error.URLError, OSError) as exc:
                if isinstance(exc, urllib.error.URLError) and not isinstance(exc, urllib.error.HTTPError):
                    # Server spento o rete giu': il file resta dov'e'.
                    LOGGER.warning("%s: server non raggiungibile (%s), riprovo", f.name, exc.reason)
                    return
                LOGGER.error("%s: %s", f.name, exc)
                sposta(f, cartella / "errori", str(exc))
            dimensioni.pop(f, None)


def main() -> int:
    ap = argparse.ArgumentParser(description="Manda allo Scanner carte gli scan salvati in una cartella.")
    ap.add_argument("cartella", nargs="?", default=str(Path.home() / "Scansioni-carte"))
    ap.add_argument("--api", help="URL del sito (sovrascrive NERDNOSTALGIA_API_URL)")
    ap.add_argument("--env-file", default=str(Path.home() / ".config/nerdnostalgia/sync.env"))
    args = ap.parse_args()

    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    carica_env_file(Path(args.env_file))
    base = args.api or os.getenv("NERDNOSTALGIA_API_URL", "")
    utente = os.getenv("NERDNOSTALGIA_USERNAME", "")
    password = os.getenv("NERDNOSTALGIA_PASSWORD", "")
    if not (base and utente and password):
        LOGGER.error("Mancano NERDNOSTALGIA_API_URL/USERNAME/PASSWORD (env o %s)", args.env_file)
        return 1
    if not shutil.which("sips"):
        LOGGER.error("sips non trovato: lo script e' pensato per macOS")
        return 1

    cartella = Path(args.cartella).expanduser()
    cartella.mkdir(parents=True, exist_ok=True)
    api = Api(base, utente, password)
    try:
        api.login()
    except Exception as exc:  # noqa: BLE001
        LOGGER.error("Login su %s fallito: %s", base, exc)
        return 1
    LOGGER.info("Osservo %s → %s (Ctrl+C per fermare)", cartella, base)

    dimensioni: Dict[Path, int] = {}
    fronti: Dict[str, int] = {}
    try:
        while True:
            giro(cartella, api, dimensioni, fronti)
            time.sleep(INTERVALLO)
    except KeyboardInterrupt:
        LOGGER.info("Fermato.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
