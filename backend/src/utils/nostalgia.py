"""
Nostalgia oltre le carte: videogiochi, console e giocattoli del catalogo con
la loro data di uscita e due righe di storia, per la rubrica del sabato
(instagram_rubriche.anni_fa).

Da un articolo si cerca la voce su Wikipedia in italiano; l'anno viene da
Wikidata (data di pubblicazione, o di nascita per le linee di giocattoli),
la descrizione dal riassunto Wikipedia, la foto, quando e' libera, da
Wikimedia Commons (le console di solito ce l'hanno, le copertine dei giochi
no). L'abbinamento e' severo: le parole del titolo Wikipedia devono essere
quelle del nostro titolo, ripulito da piattaforma, regione e simili. Meglio
saltare un articolo che raccontare il gioco sbagliato.
"""
import logging
import re
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import quote

from utils import card_names_it

LOGGER = logging.getLogger("nostalgia")

# Wikipedia vuole un User-Agent che dica chi chiama e risponde 429 a chi
# chiede troppo in fretta: una richiesta ogni PAUSA secondi, poi la cache.
UA = {"User-Agent": "NerdNostalgia/1.0 (https://nerdnostalgia.store; nerdnostalgiaita@gmail.com)"}
PAUSA = 1.0
_ultima = [0.0]


def _get(url: str, params: Optional[dict] = None) -> Optional[dict]:
    import requests
    attesa = PAUSA - (time.monotonic() - _ultima[0])
    if attesa > 0:
        time.sleep(attesa)
    _ultima[0] = time.monotonic()
    try:
        r = requests.get(url, params=params, headers=UA, timeout=20)
    except requests.RequestException as exc:
        LOGGER.info("Wikipedia non risponde (%s)", exc)
        return None
    if r.status_code != 200:
        LOGGER.info("Wikipedia: %s per %s", r.status_code, url)
        return None
    try:
        return r.json()
    except ValueError:
        return None

WIKI = "https://it.wikipedia.org"
WIKIDATA = "https://www.wikidata.org/wiki/Special:EntityData/{}.json"
COMMONS = "https://commons.wikimedia.org/wiki/Special:FilePath/{}?width=1200"

# Parole del titolo che non sono il nome del gioco.
RUMORE = {
    "wii", "wiiu", "u", "ds", "3ds", "2ds", "ps1", "psx", "ps2", "ps3", "ps4", "ps5", "psp", "vita", "ps",
    "playstation", "xbox", "360", "one", "series", "x", "s", "switch", "gamecube", "gc", "n64", "nes",
    "snes", "gb", "gba", "gbc", "game", "boy", "advance", "color", "megadrive", "genesis", "pc", "cd",
    "dvd", "jpn", "jap", "jp", "pal", "ita", "eng", "usa", "ntsc", "eu", "uk", "fr", "es", "de",
    "cib", "completo", "completa", "nuovo", "nuova", "sigillato", "sigillata", "usato", "usata",
    "originale", "edizione", "versione", "con", "senza", "scatola", "manuale", "box", "loose", "solo",
    "gioco", "videogioco", "cartuccia", "disco", "il", "lo", "la", "i", "gli", "le", "di", "del",
    "della", "e", "the", "of", "a", "and", "nintendo", "sony", "microsoft", "sega", "sealed", "deluxe",
    "edition", "first", "lotto", "funzionante", "controller", "giochi", "nera", "bianca", "jpn",
}
# Piattaforme scritte per esteso: si tolgono prima di spezzare in parole,
# altrimenti il numero ("PlayStation 4") resterebbe e farebbe saltare l'abbinamento.
PIATTAFORME = re.compile(
    r"\b(playstation\s*[1-5]|ps\s*[1-5]|xbox\s*(one|360|series\s*[xs])?|nintendo\s*(switch|wii\s*u?|ds|3ds|64|gamecube)"
    r"|game\s*boy(\s*(advance|color))?|wii\s*u|super\s*nintendo|mega\s*drive)\b", re.IGNORECASE)
# Le linee di giocattoli: la pagina Wikipedia giusta e l'anno se Wikidata non lo ha.
LINEE = {"Gormiti": ("Gormiti", 2005), "Bakugan": ("Bakugan - Battle Brawlers", 2007), "Beyblade": ("Beyblade", 1999)}
VIDEOGIOCO = "Q7889"
TIPI_CONSOLE = {"Q62008942", "Q8076", "Q941818", "Q1032372", "Q16967479"}


@dataclass
class Voce:
    titolo: str                      # come su Wikipedia
    anno: int
    data: Optional[str]              # "1996-06-23" se nota al giorno
    riassunto: str
    pagina: str
    foto: Optional[str] = None       # URL Commons, solo se libera
    tipo: str = "videogioco"         # videogioco, console, giocattolo
    extra: Dict[str, str] = field(default_factory=dict)


def _parole(testo: str) -> List[str]:
    testo = unicodedata.normalize("NFKD", testo or "").encode("ascii", "ignore").decode().lower()
    return [p for p in re.split(r"[^a-z0-9]+", testo) if p]


def _nucleo(testo: str) -> set:
    return {p for p in _parole(PIATTAFORME.sub(" ", testo or "")) if p not in RUMORE}


def stesso_titolo(nostro: str, wikipedia: str) -> bool:
    """Le parole importanti del titolo Wikipedia (senza le precisazioni tra
    parentesi) sono tutte nel nostro, e nel nostro ne avanza al massimo una:
    "Super Mario Galaxy nintendo wii" va, "Prince of Persia i due troni e le
    sabbie del tempo" con "Prince of Persia: I due troni" no."""
    wiki = _nucleo(re.sub(r"\(.*?\)", "", wikipedia))
    noi = _nucleo(nostro)
    return len(wiki) >= 1 and wiki <= noi and len(noi - wiki) <= 1


def _cerca(query: str) -> Optional[str]:
    r = card_names_it._in_cache(
        f"wiki:cerca:{query}",
        lambda: _get(f"{WIKI}/w/api.php", {"action": "query", "list": "search", "srsearch": query,
                                                        "format": "json", "srlimit": 3}))
    risultati = ((r or {}).get("query") or {}).get("search") or []
    return [x["title"] for x in risultati] or None


def _anno_data(claims: dict, proprieta: str) -> Optional[str]:
    for c in claims.get(proprieta, []):
        valore = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(valore, dict) and valore.get("time"):
            return valore["time"].lstrip("+")[:10]
    return None


def voce(titolo_pagina: str, tipo: str) -> Optional[Voce]:
    riassunto = card_names_it._in_cache(
        f"wiki:sommario:{titolo_pagina}",
        lambda: _get(f"{WIKI}/api/rest_v1/page/summary/{quote(titolo_pagina.replace(' ', '_'))}"))
    if not isinstance(riassunto, dict) or not riassunto.get("wikibase_item"):
        return None
    qid = riassunto["wikibase_item"]
    dati = card_names_it._in_cache(f"wikidata:{qid}", lambda: _get(WIKIDATA.format(qid)))
    entita = ((dati or {}).get("entities") or {}).get(qid) or {}
    claims = entita.get("claims") or {}
    istanze = {((c.get("mainsnak") or {}).get("datavalue") or {}).get("value", {}).get("id")
               for c in claims.get("P31", [])}
    if tipo == "videogioco" and VIDEOGIOCO not in istanze:
        return None
    if tipo == "console" and not istanze & TIPI_CONSOLE:
        return None
    data = _anno_data(claims, "P577") or _anno_data(claims, "P571") or _anno_data(claims, "P580")
    if not data or not data[:4].isdigit():
        return None
    foto = None
    for c in claims.get("P18", [])[:1]:
        nome = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(nome, str):
            foto = COMMONS.format(quote(nome.replace(" ", "_")))
    giorno_noto = data[5:7] != "00" and data[8:10] != "00"
    return Voce(titolo=riassunto.get("title") or titolo_pagina, anno=int(data[:4]),
                data=data if giorno_noto else None, riassunto=(riassunto.get("extract") or "").strip(),
                pagina=((riassunto.get("content_urls") or {}).get("desktop") or {}).get("page")
                or f"{WIKI}/wiki/{quote(titolo_pagina)}",
                foto=foto, tipo=tipo)


def per_articolo(titolo: str, tipo: str) -> Optional[Voce]:
    """La voce Wikipedia di un nostro articolo, se l'abbinamento e' sicuro."""
    nucleo = " ".join(p for p in _parole(PIATTAFORME.sub(" ", titolo)) if p not in RUMORE)
    if not nucleo:
        return None
    aggiunta = {"videogioco": " videogioco", "console": " console"}.get(tipo, "")
    for query in (nucleo + aggiunta, nucleo):
        for pagina in _cerca(query) or []:
            if tipo == "giocattolo" or stesso_titolo(titolo, pagina):
                trovata = voce(pagina, tipo)
                if trovata is not None:
                    return trovata
    return None


def per_linea(nome: str) -> Optional[Voce]:
    """Una linea di giocattoli (Gormiti, Bakugan, Beyblade): la sua pagina
    Wikipedia; se Wikidata non ha la data, l'anno noto."""
    pagina, anno = LINEE.get(nome, (nome, None))
    trovata = voce(pagina, "giocattolo")
    if trovata is None and anno:
        riassunto = card_names_it._in_cache(
            f"wiki:sommario:{pagina}",
            lambda: _get(f"{WIKI}/api/rest_v1/page/summary/{quote(pagina.replace(' ', '_'))}"))
        if isinstance(riassunto, dict) and riassunto.get("extract"):
            trovata = Voce(titolo=nome, anno=anno, data=None, riassunto=riassunto["extract"].strip(),
                           pagina=((riassunto.get("content_urls") or {}).get("desktop") or {}).get("page")
                           or f"{WIKI}/wiki/{quote(pagina)}", tipo="giocattolo")
    return trovata


def frasi(testo: str, quante: int = 2, massimo: int = 320) -> str:
    """Le prime frasi del riassunto, senza superare `massimo` caratteri."""
    pezzi = re.split(r"(?<=[.!?])\s+", testo.strip())
    out = ""
    for p in pezzi[:quante]:
        if len(out) + len(p) + 1 > massimo:
            break
        out = (out + " " + p).strip()
    return out or testo[:massimo].rsplit(" ", 1)[0] + "…"
