#!/usr/bin/env python3
"""
Sincronizzazione giornaliera della cartella dello scanner (Windows o Mac).

Diverso da scanner_watch.py, che resta acceso e sposta i file: questo
gira una volta (di solito al giorno, dall'Utilita' di pianificazione di
Windows), confronta la cartella con lo STATO salvato al giro precedente e
manda allo Scanner carte solo il diff — i file nuovi o cambiati. La
cartella non viene toccata.

Lo stato e' l'impronta (SHA-1) del CONTENUTO di ogni file gia' caricato:
un file rinominato o spostato in un'altra sottocartella non si ricarica,
uno modificato si'. Un file che non si riesce a caricare non entra nello
stato, cosi' il giro dopo ci si riprova da solo.

Dopo il caricamento, le carte riconosciute con certezza (confidenza alta,
nessuna versione quasi identica) vanno dritte in collezione, gia'
valutate; le altre restano in "Da confermare" nella pagina.

Il retro di una carta si chiama come il fronte con "_retro" (o "_back")
in fondo: carta12.jpg + carta12_retro.jpg. Si carica dopo il fronte e
prima della conferma, perche' la condizione si stima meglio col retro.

Uso:
    python scanner_sync.py                 # un giro con la configurazione salvata
    python scanner_sync.py --configura     # crea/modifica la configurazione
    python scanner_sync.py --prova         # dice cosa caricherebbe, senza caricare

Configurazione (scanner_sync.ini), in:
    Windows: %APPDATA%\\NerdNostalgia\\
    Mac/Linux: ~/.config/nerdnostalgia/
accanto allo stato (stato-<cartella>.json) e al log (scanner_sync.log).

Dipendenze: Python 3.9+ e Pillow (pip install pillow) per ridurre gli scan
grossi, TIFF compresi. Senza Pillow su Mac si usa `sips`; su Windows i file
oltre il limite del server vengono segnalati e saltati.
"""
import argparse
import configparser
import getpass
import hashlib
import io
import json
import logging
import logging.handlers
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
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

LOGGER = logging.getLogger("scanner_sync")

ESTENSIONI = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp", ".heic"}
LATO_MAX = 2400          # come la pagina: basta e avanza per leggere il numero
LIMITE_SERVER = 5 * 1024 * 1024
RE_RETRO = re.compile(r"^(.*?)[\s_-]*(retro|back)$", re.I)
# Il gioco di una carta: dal nome di una cartella nel suo percorso
# (Carte/Pokemon/2026-11-16/carta01.jpg → Pokemon), altrimenti quello della
# configurazione, altrimenti quello scelto nella pagina Scanner carte.
GIOCHI = {
    "pokemon": 5, "pokémon": 5,
    "magic": 1, "mtg": 1, "magicthegathering": 1,
    "yugioh": 4, "ygo": 4,
    "onepiece": 15, "op": 15,
}


def gioco_da_percorso(rel: Path) -> Optional[int]:
    for parte in reversed(rel.parent.parts):
        chiave = re.sub(r"[\s_\-!.']", "", parte.lower())
        if chiave in GIOCHI:
            return GIOCHI[chiave]
    return None


# Un file appena scritto dallo scanner potrebbe essere incompleto: si
# prende solo se non e' cambiato negli ultimi secondi.
ETA_MINIMA_SECONDI = 30


# ── Percorsi e configurazione ────────────────────────────────────

def cartella_dati() -> Path:
    if os.environ.get("NN_SCANNER_SYNC_DIR"):  # prove, o piu' configurazioni
        return Path(os.environ["NN_SCANNER_SYNC_DIR"])
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return base / "NerdNostalgia"
    return Path.home() / ".config" / "nerdnostalgia"


def file_config() -> Path:
    return cartella_dati() / "scanner_sync.ini"


def leggi_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read(file_config(), encoding="utf-8")
    if not cfg.has_section("scanner"):
        cfg.add_section("scanner")
    return cfg


def configura() -> None:
    """Domande a terminale, una volta sola. La password resta nel file di
    configurazione: lo si tiene nella cartella dati dell'utente, non in
    una cartella condivisa."""
    cfg = leggi_config()
    s = cfg["scanner"]

    def chiedi(chiave, domanda, default=""):
        attuale = s.get(chiave, default)
        risposta = input(f"{domanda} [{attuale}]: ").strip()
        s[chiave] = risposta or attuale

    chiedi("cartella", "Cartella dove lo scanner salva le carte")
    chiedi("api", "Indirizzo del sito", "https://api.nerdnostalgia.store")
    chiedi("utente", "Utente admin")
    pwd = getpass.getpass("Password admin (invio = lascia quella salvata): ")
    if pwd:
        s["password"] = pwd
    chiedi("gioco", "Gioco se la cartella non lo dice (pokemon/magic/yugioh/onepiece, vuoto = quello della pagina)")
    chiedi("auto_conferma", "Mettere in collezione da sole le carte sicure? (si/no)", "si")
    chiedi("valuta_subito", "Valutarle subito (CardTrader + eBay)? (si/no)", "si")
    cartella_dati().mkdir(parents=True, exist_ok=True)
    with open(file_config(), "w", encoding="utf-8") as fh:
        cfg.write(fh)
    if os.name != "nt":
        os.chmod(file_config(), 0o600)
    print(f"Salvata in {file_config()}")


def file_stato(cartella: Path) -> Path:
    """Uno stato per cartella: se un giorno si cambia cartella, non si
    confonde con la vecchia."""
    chiave = hashlib.sha1(str(cartella.resolve()).lower().encode()).hexdigest()[:10]
    return cartella_dati() / f"stato-{chiave}.json"


def leggi_stato(cartella: Path) -> dict:
    try:
        return json.loads(file_stato(cartella).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {"cartella": str(cartella), "file": {}}


def salva_stato(cartella: Path, stato: dict) -> None:
    """Scrittura atomica: un PC spento a meta' non deve lasciare uno stato
    rotto (che farebbe ricaricare tutto)."""
    dest = file_stato(cartella)
    tmp = dest.with_suffix(".tmp")
    tmp.write_text(json.dumps(stato, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, dest)


# ── File ─────────────────────────────────────────────────────────

def impronta(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for blocco in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(blocco)
    return h.hexdigest()


def elenca(cartella: Path) -> List[Path]:
    """Tutte le immagini, anche nelle sottocartelle (molti scanner ne
    creano una per giorno)."""
    adesso = time.time()
    out = []
    for p in cartella.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in ESTENSIONI or p.name.startswith("."):
            continue
        # Ancora in scrittura: al prossimo giro. Una data nel futuro (orologio
        # del PC sbagliato) non conta come "appena scritto", se no il file
        # resterebbe fuori fino a quel giorno.
        if 0 <= adesso - p.stat().st_mtime < ETA_MINIMA_SECONDI:
            continue
        out.append(p)
    return sorted(out)


def nome_fronte(p: Path) -> Optional[str]:
    m = RE_RETRO.match(p.stem)
    return m.group(1) if m else None


def jpeg_ridotto(path: Path) -> bytes:
    """JPEG con il lato lungo a LATO_MAX px: il server accetta pochi MB, uno
    scan a 600 dpi ne pesa decine."""
    try:
        from PIL import Image, ImageOps
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((LATO_MAX, LATO_MAX))
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=92)
            return buf.getvalue()
    except ImportError:
        pass
    if shutil.which("sips"):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "x.jpg"
            subprocess.run(["sips", "-Z", str(LATO_MAX), "-s", "format", "jpeg", str(path), "--out", str(out)],
                           capture_output=True, check=True)
            return out.read_bytes()
    dati = path.read_bytes()
    if len(dati) > LIMITE_SERVER or path.suffix.lower() in (".tif", ".tiff", ".bmp", ".heic"):
        raise RuntimeError("file troppo grande o in un formato da convertire: installa Pillow (pip install pillow)")
    return dati


# ── API ──────────────────────────────────────────────────────────

class Api:
    def __init__(self, base: str, utente: str, password: str):
        self.base = base.rstrip("/")
        self.utente = utente
        self.password = password
        self.token: Optional[str] = None

    def login(self) -> None:
        dati = urllib.parse.urlencode({"username": self.utente, "password": self.password}).encode()
        with urllib.request.urlopen(f"{self.base}/api/auth/login", data=dati, timeout=30) as r:
            self.token = json.load(r)["access_token"]

    def _richiesta(self, metodo: str, path: str, corpo: Optional[bytes] = None,
                   tipo: Optional[str] = None, timeout: int = 180):
        for tentativo in (1, 2):
            if not self.token:
                self.login()
            req = urllib.request.Request(f"{self.base}{path}", data=corpo, method=metodo)
            req.add_header("Authorization", f"Bearer {self.token}")
            if tipo:
                req.add_header("Content-Type", tipo)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return json.load(r)
            except urllib.error.HTTPError as exc:
                if exc.code == 401 and tentativo == 1:
                    self.token = None  # token scaduto: si rifa' il login
                    continue
                dettaglio = exc.read().decode("utf-8", "ignore")[:300]
                try:
                    dettaglio = json.loads(dettaglio).get("detail", dettaglio)
                except ValueError:
                    pass
                raise RuntimeError(f"HTTP {exc.code}: {dettaglio}") from exc
        raise RuntimeError("login non riuscito")

    def invia(self, path: str, nome: str, dati: bytes, campi: Optional[dict] = None) -> dict:
        confine = uuid.uuid4().hex
        extra = "".join(
            f"--{confine}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n"
            for k, v in (campi or {}).items() if v is not None
        )
        corpo = (
            extra +
            f"--{confine}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{nome}\"\r\n"
            f"Content-Type: image/jpeg\r\n\r\n"
        ).encode() + dati + f"\r\n--{confine}--\r\n".encode()
        return self._richiesta("POST", path, corpo, f"multipart/form-data; boundary={confine}")

    def auto_conferma(self, scan_id: int, valuta: bool) -> dict:
        q = "true" if valuta else "false"
        return self._richiesta("POST", f"/api/card-scanner/scans/{scan_id}/auto-confirm?price_now={q}")


# ── Il giro ──────────────────────────────────────────────────────

def giro(cartella: Path, api: Optional[Api], auto: bool, valuta: bool, prova: bool,
         gioco_default: Optional[int] = None) -> int:
    stato = leggi_stato(cartella)
    noti: Dict[str, dict] = stato["file"]  # impronta → {percorso, scan_id, esito, quando}
    file = elenca(cartella)
    impronte = {p: impronta(p) for p in file}
    nuovi = [p for p in file if impronte[p] not in noti]
    # Fronti prima dei retro: un retro si attacca al suo fronte.
    nuovi.sort(key=lambda p: nome_fronte(p) is not None)

    LOGGER.info("Cartella %s: %d file, %d nuovi o cambiati", cartella, len(file), len(nuovi))
    if not nuovi:
        return 0
    if prova:
        for p in nuovi:
            rel = p.relative_to(cartella)
            g = gioco_da_percorso(rel) or gioco_default
            LOGGER.info("  caricherei %s (%s)", rel, f"gioco {g}" if g else "gioco della pagina")
        return 0

    # Fronti gia' caricati (anche nei giorni scorsi), per attaccarci i retro
    fronti: Dict[str, int] = {
        Path(v["percorso"]).stem: v["scan_id"] for v in noti.values()
        if v.get("scan_id") and nome_fronte(Path(v["percorso"])) is None
    }
    da_confermare: List[int] = []
    conteggi = {"caricati": 0, "in_collezione": 0, "da_confermare": 0, "errori": 0}

    for p in nuovi:
        rel = str(p.relative_to(cartella))
        try:
            base = nome_fronte(p)
            if base is None:
                gioco = gioco_da_percorso(p.relative_to(cartella)) or gioco_default
                scan = api.invia("/api/card-scanner/scans", p.stem + ".jpg", jpeg_ridotto(p),
                                 {"game_id": gioco})
                fronti[p.stem] = scan["id"]
                da_confermare.append(scan["id"])
                primo = (scan.get("candidates") or [{}])[0]
                LOGGER.info("%s → %s %s (%s)", rel, primo.get("name", "nessun candidato"),
                            primo.get("number", ""), scan.get("confidence"))
                esito = {"scan_id": scan["id"], "esito": "caricato"}
            else:
                scan_id = fronti.get(base)
                if scan_id is None:
                    LOGGER.info("%s: il fronte «%s» non c'e' ancora, riprovo al prossimo giro", rel, base)
                    continue
                api.invia(f"/api/card-scanner/scans/{scan_id}/back", p.stem + ".jpg", jpeg_ridotto(p))
                LOGGER.info("%s → retro dello scan %s", rel, scan_id)
                esito = {"scan_id": scan_id, "esito": "retro"}
            conteggi["caricati"] += 1
            noti[impronte[p]] = {"percorso": rel, "quando": datetime.now().isoformat(timespec="seconds"), **esito}
            salva_stato(cartella, stato)  # dopo ogni file: un'interruzione non fa ricaricare
        except urllib.error.URLError as exc:
            if not isinstance(exc, urllib.error.HTTPError):
                LOGGER.error("Server non raggiungibile (%s): mi fermo, riprovo al prossimo giro", exc.reason)
                conteggi["errori"] += 1
                break
            raise
        except Exception as exc:  # noqa: BLE001 — un file rotto non ferma gli altri
            LOGGER.error("%s: %s", rel, exc)
            conteggi["errori"] += 1

    # Conferma automatica DOPO i retro: con il retro la condizione si stima meglio.
    for scan_id in da_confermare:
        if not auto:
            conteggi["da_confermare"] += 1
            continue
        try:
            r = api.auto_conferma(scan_id, valuta)
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("Conferma automatica dello scan %s non riuscita: %s", scan_id, exc)
            conteggi["da_confermare"] += 1
            continue
        if r.get("confirmed"):
            conteggi["in_collezione"] += 1
            c = r.get("card") or {}
            LOGGER.info("  in collezione: %s · %s %s", c.get("name"), c.get("collection"), c.get("printed_code"))
        else:
            conteggi["da_confermare"] += 1
            LOGGER.info("  scan %s da confermare nella pagina: %s", scan_id, r.get("reason"))

    LOGGER.info("Fatto: %(caricati)d caricati, %(in_collezione)d in collezione, "
                "%(da_confermare)d da confermare nella pagina, %(errori)d errori", conteggi)
    return 1 if conteggi["errori"] else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Carica sullo Scanner carte i file nuovi della cartella dello scanner.")
    ap.add_argument("--configura", action="store_true", help="crea o modifica la configurazione")
    ap.add_argument("--prova", action="store_true", help="elenca cosa caricherebbe, senza caricare")
    ap.add_argument("--cartella", help="sovrascrive la cartella della configurazione")
    ap.add_argument("--api", help="sovrascrive l'indirizzo del sito (es. http://localhost:7373)")
    args = ap.parse_args()

    if args.configura:
        configura()
        return 0

    cartella_dati().mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.handlers.RotatingFileHandler(cartella_dati() / "scanner_sync.log",
                                                 maxBytes=1_000_000, backupCount=3, encoding="utf-8"),
        ],
    )
    s = leggi_config()["scanner"]
    cartella = Path(args.cartella or s.get("cartella", "")).expanduser()
    if not str(cartella) or not cartella.is_dir():
        LOGGER.error("Cartella non trovata: «%s». Lancia: python scanner_sync.py --configura", cartella)
        return 2

    api = None
    if not args.prova:
        base, utente, password = args.api or s.get("api", ""), s.get("utente", ""), s.get("password", "")
        if not (base and utente and password):
            LOGGER.error("Configurazione incompleta. Lancia: python scanner_sync.py --configura")
            return 2
        api = Api(base, utente, password)
        try:
            api.login()
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("Login su %s non riuscito: %s", base, exc)
            return 3

    si = lambda v: str(v).strip().lower() in ("si", "sì", "s", "yes", "y", "1", "true")  # noqa: E731
    gioco = s.get("gioco", "").strip()
    gioco_default = GIOCHI.get(re.sub(r"[\s_\-!.']", "", gioco.lower())) or (int(gioco) if gioco.isdigit() else None)
    return giro(cartella, api, si(s.get("auto_conferma", "si")), si(s.get("valuta_subito", "si")), args.prova,
                gioco_default)


if __name__ == "__main__":
    sys.exit(main())
