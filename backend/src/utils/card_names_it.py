"""
Nomi italiani delle carte (e dei set, dove esistono).

CardTrader ha i nomi solo in inglese, ma una carta italiana si chiama come
c'e' stampato sopra ("Scintille Folgoranti", non "Surging Sparks") ed e'
cosi' che la cercano i compratori italiani. Le fonti, una per gioco:

  - Pokemon: TCGdex (carta e set), dal nome inglese del set + numero;
  - Magic: Scryfall (solo la carta: i set hanno il nome inglese anche nelle
    edizioni italiane), da codice set + numero;
  - Yu-Gi-Oh: YGOPRODeck (solo la carta), dal codice stampato (LOB-IT005);
  - One Piece: non esce in italiano, niente.

Tutto best-effort: una fonte che non risponde lascia i nomi inglesi, mai
una carta bloccata.
"""
import logging
import re
import time
from typing import Dict, Optional, Tuple

import requests

LOGGER = logging.getLogger("card_names_it")

TIMEOUT = 10
UA = {"User-Agent": "NerdNostalgia/1.0 (nerdnostalgia.store)", "Accept": "application/json"}

POKEMON, MAGIC, YUGIOH = 5, 1, 4

_CACHE_SET_TTL = 24 * 3600
_cache_set: Dict[str, Tuple[float, object]] = {}


def _get(url: str, params: Optional[dict] = None) -> Optional[dict]:
    try:
        resp = requests.get(url, params=params, headers=UA, timeout=TIMEOUT)
    except requests.RequestException as exc:
        LOGGER.info("Nomi italiani: %s non risponde (%s)", url, exc)
        return None
    if resp.status_code != 200:
        return None
    try:
        return resp.json()
    except ValueError:
        return None


def _in_cache(chiave: str, carica):
    ora = time.time()
    hit = _cache_set.get(chiave)
    if hit and ora - hit[0] < _CACHE_SET_TTL:
        return hit[1]
    valore = carica()
    if valore is not None:
        _cache_set[chiave] = (ora, valore)
    return valore


def _norm(testo: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (testo or "").lower())


def _numero(codice: Optional[str]) -> Optional[str]:
    """"004/191" → "004"; "TG05/TG30" → "TG05"."""
    if not codice:
        return None
    return codice.split("/")[0].strip() or None


# ── Pokemon (TCGdex) ────────────────────────────────────────────────

def _set_pokemon(nome_inglese: str) -> Optional[str]:
    """Id TCGdex del set dal nome inglese (quello di CardTrader)."""
    elenco = _in_cache("tcgdex:en", lambda: _get("https://api.tcgdex.net/v2/en/sets"))
    if not isinstance(elenco, list):
        return None
    cercato = _norm(nome_inglese)
    # CardTrader chiama i set dell'era EX "EX Crystal Guardians", TCGdex
    # "Crystal Guardians": se non c'e' il nome esatto, si riprova senza.
    candidati = [cercato] + ([cercato[2:]] if cercato.startswith("ex") and len(cercato) > 2 else [])
    for nome in candidati:
        for s in elenco:
            if _norm(s.get("name")) == nome:
                return s.get("id")
    return None


def _pokemon(nome_set: Optional[str], codice: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    set_id = _set_pokemon(nome_set or "")
    if not set_id:
        return None, None
    info = _in_cache(f"tcgdex:it:{set_id}", lambda: _get(f"https://api.tcgdex.net/v2/it/sets/{set_id}"))
    set_it = info.get("name") if isinstance(info, dict) else None
    numero = _numero(codice)
    nome_it = None
    if numero and isinstance(info, dict):
        # Il localId e' come stampato: "004" nei set recenti, "4" nei vecchi.
        varianti = {numero, numero.lstrip("0") or "0", numero.zfill(3)}
        for c in info.get("cards") or []:
            if c.get("localId") in varianti:
                nome_it = c.get("name")
                break
    return nome_it, set_it


# ── Magic (Scryfall) ────────────────────────────────────────────────

def _magic(codice_set: Optional[str], numero: Optional[str]) -> Optional[str]:
    if not codice_set or not numero:
        return None
    carta = _get(f"https://api.scryfall.com/cards/{codice_set.lower()}/{numero}/it")
    return (carta or {}).get("printed_name")


# ── Yu-Gi-Oh (YGOPRODeck) ───────────────────────────────────────────

def _yugioh(codice: Optional[str]) -> Optional[str]:
    """Dal codice stampato: LOB-IT005 → LOB-EN005 → id della carta → nome IT."""
    if not codice or "-" not in codice:
        return None
    inglese = re.sub(r"-[A-Z]{1,2}(\d)", r"-EN\1", codice.upper(), count=1)
    stampa = _get("https://db.ygoprodeck.com/api/v7/cardsetsinfo.php", {"setcode": inglese})
    carta_id = (stampa or {}).get("id")
    if not carta_id:
        return None
    dati = _get("https://db.ygoprodeck.com/api/v7/cardinfo.php", {"id": carta_id, "language": "it"})
    voci = (dati or {}).get("data") or []
    return voci[0].get("name") if voci else None


def cerca(game_id: Optional[int], nome_set: Optional[str], codice: Optional[str],
          codice_set: Optional[str] = None, numero: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """(nome carta, nome set) in italiano; None dove non si trova."""
    try:
        if game_id == POKEMON:
            return _pokemon(nome_set, codice or numero)
        if game_id == MAGIC:
            return _magic(codice_set, numero or _numero(codice)), None
        if game_id == YUGIOH:
            return _yugioh(codice), None
    except Exception as exc:  # noqa: BLE001 — mai bloccare la carta per un nome
        LOGGER.warning("Nomi italiani non trovati (gioco %s, %s): %s", game_id, codice, exc)
    return None, None
