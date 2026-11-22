"""
Lettura di una carta scansionata: ritaglio, OCR e codici stampati.

Una carta si riconosce dal simbolo dell'espansione e dal numero. Il
simbolo e' un disegno, e un disegno non si legge: ci pensa il confronto
d'immagine (vedi card_index). Qui si legge il TESTO che lo accompagna,
che a seconda del gioco dice molto o poco:

- Pokemon: "025/165" in basso; dai set Spada e Scudo in poi anche la
  sigla del set accanto ("SSP EN"). Sui set vecchi solo il numero.
- Magic: "0133" o "133/281 R" e sotto "DMU • EN".
- Yu-Gi-Oh!: "LOB-EN001" sotto l'illustrazione, sigla e numero insieme.
- One Piece: "OP01-064" in basso a destra.

Lo scan e' pulito (niente prospettiva, niente riflessi), quindi bastano
Tesseract e qualche ritaglio mirato: il numero e' piccolo, e ingrandito
da solo si legge molto meglio che dentro la carta intera.

Tesseract si chiama come processo: pytesseract farebbe la stessa cosa
con una dipendenza in piu'.
"""
import io
import logging
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from typing import List, Optional

from PIL import Image, ImageChops, ImageFilter, ImageOps

LOGGER = logging.getLogger("card_ocr")

OCR_TIMEOUT = 20

# Altezza a cui si porta la carta prima dell'OCR: il numero in basso deve
# uscire alto una trentina di pixel, che e' dove Tesseract rende meglio.
OCR_CARD_HEIGHT = 2000

# Lingue stampate sulle carte → codice lingua CardTrader.
LINGUE = {
    "EN": "en", "IT": "it", "FR": "fr", "DE": "de", "ES": "es", "SP": "es",
    "PT": "pt", "JP": "jp", "JA": "jp",
    # Yu-Gi-Oh! vecchio stile: una lettera sola dopo il trattino (SDK-I001)
    "E": "en", "I": "it", "F": "fr", "G": "de", "S": "es", "P": "pt",
}

# Parole che sembrano sigle di set ma sono altro testo della carta.
NON_SIGLE = {
    "HP", "PS", "EX", "GX", "VMAX", "VSTAR", "TAG", "LV", "ATK", "DEF",
    "THE", "AND", "TCG", "LLC", "INC", "KONAMI", "NINTENDO", "WIZARDS",
}


class OcrUnavailable(Exception):
    """Tesseract non installato sulla macchina."""


@dataclass
class LetturaCarta:
    """Quello che si e' riusciti a leggere. Ogni campo puo' mancare."""
    number: Optional[str] = None        # numero come sul blueprint: "025", "OP01-064"
    # Altre letture possibili del numero quando l'OCR e' ambiguo
    # ("OPOS-O76" → OP05-076 o OP08-076): le valuta il confronto d'immagine.
    alt_numbers: List[str] = field(default_factory=list)
    # Il numero e la sigla COSI' COME LETTI, prima di ogni correzione: alla
    # conferma si confrontano col vero e se ne imparano gli errori.
    raw_number: Optional[str] = None
    raw_set: Optional[str] = None
    total: Optional[str] = None         # Pokemon/Magic: il "/165"
    set_code: Optional[str] = None      # sigla espansione: "SSP", "LOB", "DMU"
    # Sigle possibili lette (anche sbagliate): le valida chi conosce le
    # espansioni vere, vedi card_index.
    set_codes: List[str] = field(default_factory=list)
    language: Optional[str] = None      # codice CardTrader: "it", "en", ...
    language_read: Optional[str] = None  # quella letta, se la pagina ne ha forzata un'altra
    # Condizione scelta nella pagina al caricamento: vince sulla stima dello scan.
    condition_forced: Optional[str] = None
    printed_code: Optional[str] = None  # cosi' com'e' stampato: "025/165", "LOB-EN001"
    name_text: str = ""                 # testo della fascia alta (il nome, piu' rumore)
    full_text: str = ""
    rotated: int = 0
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def is_available() -> bool:
    return shutil.which("tesseract") is not None


# ── Immagine ──────────────────────────────────────────────────────

def load_image(raw: bytes) -> Image.Image:
    with Image.open(io.BytesIO(raw)) as img:
        img = ImageOps.exif_transpose(img)
        return img.convert("RGB")


def crop_to_card(img: Image.Image) -> Image.Image:
    """Toglie il piano dello scanner attorno alla carta.

    Il colore del fondo lo dice l'angolo in alto a sinistra; tutto cio'
    che se ne discosta e' carta. Se il ritaglio viene minuscolo (carta
    piu' chiara del fondo in un angolo, scan gia' rifilato) si tiene
    l'immagine com'e': meglio un bordo in piu' che mezza carta in meno.
    """
    fondo = Image.new("RGB", img.size, img.getpixel((2, 2)))
    diff = ImageChops.difference(img, fondo).convert("L")
    diff = diff.point(lambda p: 255 if p > 40 else 0).filter(ImageFilter.MedianFilter(5))
    box = diff.getbbox()
    if not box:
        return img
    w, h = box[2] - box[0], box[3] - box[1]
    if w * h < 0.3 * img.width * img.height:
        return img
    return img.crop(box)


def upright(img: Image.Image) -> Image.Image:
    """Le carte sono verticali: uno scan orizzontale e' girato di 90°."""
    if img.width > img.height * 1.1:
        return img.rotate(90, expand=True)
    return img


def prepare(raw: bytes) -> Image.Image:
    card = upright(crop_to_card(load_image(raw)))
    return card.rotate(-orientation(card), expand=True) if is_available() else card


RE_OSD = re.compile(r"Rotate:\s*(\d+).*?Orientation confidence:\s*([\d.]+)", re.S)


def orientation(card: Image.Image) -> int:
    """Gradi di cui ruotare (in senso orario) per raddrizzare la carta,
    secondo l'OSD di Tesseract. Sotto una confidenza minima si lascia
    com'e': una carta dritta girata per sbaglio e' peggio di niente."""
    g = _grigio(card, OCR_CARD_HEIGHT / card.height)
    buf = io.BytesIO()
    g.save(buf, format="PNG")
    try:
        res = subprocess.run(
            ["tesseract", "stdin", "stdout", "--psm", "0"],
            input=buf.getvalue(), capture_output=True, timeout=OCR_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return 0
    m = RE_OSD.search(res.stdout.decode("utf-8", errors="ignore"))
    if not m or float(m.group(2)) < 0.5:
        return 0
    return int(m.group(1)) % 360


# ── Tesseract ─────────────────────────────────────────────────────

def _tesseract(img: Image.Image, psm: int, whitelist: Optional[str] = None) -> str:
    if not is_available():
        raise OcrUnavailable("Tesseract non installato")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    cmd = ["tesseract", "stdin", "stdout", "--psm", str(psm), "-l", "eng"]
    if whitelist:
        cmd += ["-c", f"tessedit_char_whitelist={whitelist}"]
    try:
        res = subprocess.run(
            cmd, input=buf.getvalue(), capture_output=True, timeout=OCR_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        LOGGER.warning("Tesseract oltre %ss (psm %s)", OCR_TIMEOUT, psm)
        return ""
    return res.stdout.decode("utf-8", errors="ignore")


def _grigio(img: Image.Image, scala: float = 1.0) -> Image.Image:
    g = ImageOps.autocontrast(img.convert("L"), cutoff=1)
    if scala != 1.0:
        g = g.resize((int(g.width * scala), int(g.height * scala)), Image.LANCZOS)
    return g


def _fascia(img: Image.Image, top: float, bottom: float) -> Image.Image:
    return img.crop((0, int(img.height * top), img.width, int(img.height * bottom)))


def _leggi_nome(fascia: Image.Image) -> str:
    """La fascia del nome, letta in piu' modi e messa insieme. Su scan
    piccoli o foto basta una ricompressione JPEG perche' una lettura sola
    non tiri fuori niente; tre letture diverse sbagliano raramente tutte.
    Il rumore in piu' non fa danni: conta solo cio' che somiglia a un
    nome di carta."""
    ingrandita = fascia.resize((fascia.width * 2, fascia.height * 2), Image.LANCZOS)
    binaria = ingrandita.point(lambda p: 255 if p > 128 else 0)
    letture = [
        _tesseract(fascia, psm=6),
        _tesseract(ingrandita, psm=11),
        _tesseract(binaria, psm=6),
    ]
    return "\n".join(t.strip() for t in letture if t.strip())


def ocr_card(card: Image.Image) -> dict:
    """Testo di tre zone: nome in alto, fascia del numero in basso, carta
    intera (il codice Yu-Gi-Oh! sta a meta', sotto l'illustrazione)."""
    scala = OCR_CARD_HEIGHT / card.height
    g = _grigio(card, scala)
    basso = _fascia(g, 0.86, 1.0)
    # Il numero e' minuscolo anche a 2000px: ingrandito ancora si legge.
    basso = basso.resize((basso.width * 2, basso.height * 2), Image.LANCZOS)
    return {
        "top": _leggi_nome(_fascia(g, 0.0, 0.12)),
        "bottom": _tesseract(basso, psm=11),
        "full": _tesseract(g, psm=11),
    }


# ── Codici stampati ───────────────────────────────────────────────

# One Piece: OP01-064, ST10-001, EB01-012, PRB01-001, P-001
RE_ONEPIECE = re.compile(r"\b((?:OP|ST|EB|PRB)\d{2}|P)\s?-\s?(\d{3})\b")
# Lo stesso, tollerando le lettere che Tesseract mette al posto delle cifre
# (il codice One Piece e' bianco su colore, e lo legge spesso "OPOS-O76").
CIFRE_SIMILI = {
    "O": "0", "Q": "0", "D": "0", "I": "1", "L": "1", "Z": "2",
    "S": "58", "B": "8", "G": "6", "T": "7",
}
MAX_LETTURE = 12


def _simili(appreso: Optional[dict]) -> dict:
    """Le confusioni fisse piu' quelle imparate dalle correzioni (vedi
    card_learning), queste ultime per prime: sono gli errori veri del tuo
    scanner."""
    out = {k: v for k, v in CIFRE_SIMILI.items()}
    for letto, veri in (appreso or {}).items():
        cifre = "".join(c for c in veri if c.isdigit())
        if cifre:
            out[letto] = cifre + "".join(c for c in out.get(letto, "") if c not in cifre)
    return out


def _re_onepiece_sporco(appreso: Optional[dict]):
    lettere = "".join(sorted(k for k in _simili(appreso) if k.isalpha()))
    return re.compile(rf"\b(OP|ST|EB|PRB)\s?([0-9{lettere}]{{2}})\s?-\s?([0-9{lettere}]{{3}})")


def _cifre_possibili(gruppo: str, appreso: Optional[dict] = None) -> List[str]:
    """"OS" → ["05", "08"]: ogni lettura numerica plausibile del gruppo,
    dalla piu' probabile. Anche una cifra puo' avere alternative, se le
    correzioni hanno insegnato che il tuo scanner le confonde (5 per 8)."""
    simili = _simili(appreso)
    out = [""]
    for ch in gruppo:
        if ch.isdigit():
            scelte = ch + "".join(c for c in (appreso or {}).get(ch, "") if c.isdigit() and c != ch)
        else:
            scelte = simili.get(ch, "")
        out = [o + c for o in out for c in scelte][:MAX_LETTURE]
    return out
# Yu-Gi-Oh!: LOB-EN001, LOB-001, SDK-I001, RA01-IT045, MP23-EN123
RE_YUGIOH = re.compile(
    r"\b([A-Z0-9]{2,4}[A-Z][A-Z0-9]{0,1}|[A-Z]{2,4}\d{0,2})\s?-\s?"
    r"(EN|IT|FR|DE|SP|PT|JP|E|I|F|G|S|P)?([A-Z]{0,2}\d{3})\b"
)
# Pokemon / Magic: 025/165, TG12/TG30, SV049/SV094, 133/281
RE_NUMERO_TOTALE = re.compile(r"\b([A-Z]{0,3}\d{1,3}[a-z]?)\s?/\s?([A-Z]{0,3}\d{2,3})\b")
# Sigla + lingua: "SSP EN", "DMU • EN", "PAL IT"
RE_SIGLA_LINGUA = re.compile(r"\b([A-Z0-9]{2,5})\s?[•·.*+\-]?\s?(EN|IT|FR|DE|ES|PT|JP)\b")
# Magic moderno senza totale: "0133" su riga a se'
RE_NUMERO_MAGIC = re.compile(r"(?:^|\s)(\d{4})(?:\s+[CURMSLT])?(?:\s|$)")


def _pulisci(testo: str) -> str:
    """Errori tipici di Tesseract sui numeri piccoli: la O letta al posto
    dello zero dentro i gruppi di cifre, i trattini lunghi."""
    t = testo.replace("—", "-").replace("–", "-").replace("|", "/")
    t = re.sub(r"(?<=\d)[Oo](?=\d)", "0", t)
    return t


# Parole che compaiono su quasi ogni carta, per lingua. Bastano poche
# occorrenze: l'OCR sbaglia le parole lunghe, ma le corte e frequenti
# ("il tuo turno", "your turn") escono quasi sempre giuste.
PAROLE_LINGUA = {
    "it": {"il", "tuo", "tua", "tuoi", "danno", "danni", "della", "dei", "puoi", "questo", "nella",
           "avversario", "segnalino", "segnalini", "difensore", "anziché", "mazzo", "metti", "volta",
           "scarta", "debolezza", "resistenza", "ritirata", "lunghezza"},
    "en": {"the", "your", "damage", "this", "card", "opponent", "you", "may", "each",
           "deck", "defending", "attack", "of", "put", "once",
           "discard", "weakness", "resistance", "retreat", "length", "weight"},
    "fr": {"le", "votre", "tour", "dégâts", "cette", "carte", "adversaire", "vous", "pouvez", "chaque",
           "défaussez", "faiblesse", "retraite", "taille", "poids"},
    "de": {"dein", "deinen", "zug", "schaden", "diese", "karte", "gegner", "du", "kannst", "der",
           "schwäche", "resistenz", "rückzug", "rückzugskosten", "größe", "gewicht"},
    "es": {"tu", "daño", "esta", "rival", "puedes", "los", "tus", "vez", "pon", "defensor",
           "descarta", "debilidad", "resistencia", "retirada", "altura"},
}
# NB: niente parole comuni a due lingue ("turno", "carta", "del", "peso",
# "costo" sono sia italiano sia spagnolo): farebbero pari e la lingua non
# si deciderebbe. Le parole fisse del riquadro in basso (debolezza,
# resistenza, ritirata, lunghezza) contano anche sulle carte con poco testo.


def detect_language(testo: str, minimo: int = 4) -> Optional[str]:
    """Lingua del testo della carta, se le parole tipiche lo dicono con
    un certo stacco. None se il testo e' troppo poco o ambiguo (o non e'
    in caratteri latini: giapponese, cinese...)."""
    parole = re.findall(r"[a-zà-ÿ]+", (testo or "").lower())
    conteggi = {lang: sum(1 for p in parole if p in insieme) for lang, insieme in PAROLE_LINGUA.items()}
    ordinati = sorted(conteggi.items(), key=lambda x: -x[1])
    (primo, n1), (_, n2) = ordinati[0], ordinati[1]
    if n1 >= minimo and n1 >= 2 * max(n2, 1):
        return primo
    return None


RE_NUMERO_SPORCO = re.compile(r"\b([0-9A-Z]{1,3})\s?/\s?([0-9A-Z]{2,3})\b")


def parse_codes(testi: dict, game_hint: Optional[str] = None,
                appreso: Optional[dict] = None) -> LetturaCarta:
    """Dai testi OCR ai codici della carta. `game_hint` ("pokemon",
    "magic", "yugioh", "onepiece") evita di cercare formati di altri
    giochi, che su una carta qualsiasi trovano sempre qualcosa."""
    top = testi.get("top", "") or ""
    bottom = _pulisci(testi.get("bottom", "") or "")
    full = _pulisci(testi.get("full", "") or "")
    out = LetturaCarta(name_text=top.strip(), full_text=full.strip())
    # In basso prima: e' la zona del numero, e li' il testo e' piu' pulito.
    zone = [bottom, full]
    alto = lambda s: s.upper()  # noqa: E731

    if game_hint in (None, "onepiece"):
        for z in zone:
            m = RE_ONEPIECE.search(alto(z))
            if m:
                out.set_code = m.group(1)
                out.set_codes = [m.group(1)]
                out.number = f"{m.group(1)}-{m.group(2)}"
                out.printed_code = out.number
                out.raw_set, out.raw_number = m.group(1), m.group(2)
                return out
        for z in zone:
            m = _re_onepiece_sporco(appreso).search(alto(z))
            if not m:
                continue
            out.raw_set, out.raw_number = m.group(1) + m.group(2), m.group(3)
            numeri = _cifre_possibili(m.group(3), appreso)
            sigle = [m.group(1) + c for c in _cifre_possibili(m.group(2), appreso)]
            codici = [f"{sg}-{n}" for sg in sigle for n in numeri]
            if codici:
                out.set_codes = sigle
                out.set_code = sigle[0]
                out.number = codici[0]
                out.alt_numbers = codici[1:]
                out.printed_code = codici[0] if len(codici) == 1 else None
                out.notes.append(f"codice letto «{m.group(0)}»: provo {', '.join(codici)}")
                return out

    if game_hint in (None, "yugioh"):
        for z in [full, bottom]:
            for m in RE_YUGIOH.finditer(alto(z)):
                sigla = m.group(1)
                if sigla in NON_SIGLE or sigla.isdigit():
                    continue
                out.set_code = sigla
                out.set_codes = [sigla]
                out.number = m.group(3)
                out.raw_set, out.raw_number = sigla, m.group(3)
                if m.group(2):
                    out.language = LINGUE.get(m.group(2))
                out.printed_code = m.group(0).replace(" ", "")
                return out

    if game_hint in (None, "pokemon", "magic"):
        for z in zone:
            m = RE_NUMERO_TOTALE.search(z)
            if m:
                out.number, out.total = m.group(1), m.group(2)
                out.printed_code = f"{m.group(1)}/{m.group(2)}"
                out.raw_number = m.group(1)
                break
        if not out.number and appreso:
            # Con le confusioni imparate: "4S/1O2" → 48/102 o 45/102.
            for z in zone:
                for m in RE_NUMERO_SPORCO.finditer(alto(z)):
                    if not any(c.isdigit() for c in m.group(0)):
                        continue
                    numeri, totali = _cifre_possibili(m.group(1), appreso), _cifre_possibili(m.group(2), appreso)
                    if numeri and totali:
                        out.number, out.total = numeri[0], totali[0]
                        out.alt_numbers = numeri[1:]
                        out.raw_number = m.group(1)
                        out.notes.append(f"numero letto «{m.group(0)}»: provo {', '.join(numeri)}")
                        break
                if out.number:
                    break
        if not out.number and game_hint == "magic":
            m = RE_NUMERO_MAGIC.search(bottom)
            if m:
                out.number = m.group(1)
                out.printed_code = m.group(1)
        # La sigla e' corta e stampata piccola: Tesseract ne sbaglia una
        # lettera su tre (DMU letta OMU). Si tengono tutte quelle plausibili
        # e si sceglie confrontandole con le espansioni che esistono.
        for z in zone:
            for m in RE_SIGLA_LINGUA.finditer(alto(z)):
                sigla = m.group(1)
                if sigla in NON_SIGLE or sigla.isdigit() or sigla in out.set_codes:
                    continue
                out.set_codes.append(sigla)
                out.raw_set = out.raw_set or sigla
                if not out.language:
                    out.language = LINGUE.get(m.group(2))
        out.set_code = out.set_codes[0] if out.set_codes else None

    if not out.number:
        out.notes.append("numero non letto")
    # La lingua dal testo vince su quella accanto alla sigla: "GE · ES"
    # puo' essere rumore letto come sigla, sedici parole italiane no. Anche
    # due sole parole bastano contro la sigla: sulle carte vecchie (Base Set)
    # la sigla di lingua non c'e', e quella trovata e' sempre rumore.
    out.language = detect_language(full) or detect_language(full, minimo=2) or out.language
    return out


def _parole_vere(testo: str) -> int:
    """Parole di almeno quattro lettere: tante su una carta dritta, quasi
    nessuna su una capovolta (dove l'OCR legge solo frammenti)."""
    return len(re.findall(r"[A-Za-zÀ-ÿ]{4,}", testo or ""))


def read_card(raw: bytes, game_hint: Optional[str] = None, appreso: Optional[dict] = None) -> tuple:
    """Scan grezzo → (immagine ritagliata e raddrizzata, LetturaCarta).

    Se il numero non salta fuori si prova la carta capovolta, ma la si
    tiene solo se si legge MEGLIO: su un testo al rovescio Tesseract
    trova comunque qualcosa che somiglia a "594/007"."""
    card = prepare(raw)
    lettura = parse_codes(ocr_card(card), game_hint, appreso)
    if not lettura.number:
        girata = card.rotate(180)
        seconda = parse_codes(ocr_card(girata), game_hint, appreso)
        if seconda.number and _parole_vere(seconda.full_text) > _parole_vere(lettura.full_text):
            seconda.rotated = 180
            return girata, seconda
    return card, lettura
