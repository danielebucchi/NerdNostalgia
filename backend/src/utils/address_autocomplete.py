"""
Suggerimenti indirizzo per il form di checkout (Geoapify Address Autocomplete).

Perche' Geoapify e non Google Places: piano gratuito senza carta di credito,
server in UE (l'indirizzo digitato non esce dallo SEE) e nessun obbligo di
mostrare una mappa accanto ai risultati.

La chiave sta SOLO lato server: il browser chiama /api/address/autocomplete e
il backend inoltra. Se la mettessimo in una NEXT_PUBLIC_* finirebbe nel bundle
e chiunque potrebbe consumare la quota.

Env:
  GEOAPIFY_API_KEY      chiave API. Vuota = endpoint attivo ma risponde
                        `configured: false` e zero suggerimenti (il form resta
                        compilabile a mano: il degrado non blocca l'acquisto).
  ADDRESS_COUNTRY_CODES codici ISO separati da virgola per limitare la
                        ricerca (default "it").
"""
import logging
import os
from typing import Any, Dict, List

import requests

LOGGER = logging.getLogger("address")

API_URL = "https://api.geoapify.com/v1/geocode/autocomplete"
TIMEOUT = 8
MAX_RESULTS = 6


class AddressError(Exception):
    pass


def _api_key() -> str:
    return (os.getenv("GEOAPIFY_API_KEY") or "").strip()


def is_configured() -> bool:
    return bool(_api_key())


def _country_filter() -> str:
    raw = (os.getenv("ADDRESS_COUNTRY_CODES") or "it").strip()
    codes = [c.strip().lower() for c in raw.split(",") if c.strip()]
    return ",".join(codes) or "it"


def _to_suggestion(feature: Dict[str, Any]) -> Dict[str, str]:
    """Normalizza una feature Geoapify nei campi del nostro form.

    `street` ricompone via + civico perche' il form ha un solo campo
    'Indirizzo (via e numero civico)'. Geoapify li tiene separati e puo'
    ometterli entrambi (es. se cerchi solo una citta').
    """
    props = feature.get("properties") or {}
    street = (props.get("street") or "").strip()
    housenumber = (props.get("housenumber") or "").strip()
    full_street = f"{street} {housenumber}".strip() if street else ""
    return {
        "label": (props.get("formatted") or "").strip(),
        "street": full_street,
        "postal_code": (props.get("postcode") or "").strip(),
        "city": (props.get("city") or props.get("town") or props.get("village") or "").strip(),
        # Provincia = county_code (sigla di 2 lettere, es. "LI"), con fallback
        # sul nome esteso. NON state_code: per l'Italia quello e' la REGIONE
        # ("TOS" per la Toscana), che nel campo Provincia sarebbe sbagliato.
        "province": (props.get("county_code") or props.get("county") or "").strip(),
        "country": (props.get("country") or "").strip(),
        # Coordinate: servono a centrare la mappa dei locker sull'indirizzo
        # scelto, cosi' il compratore vede subito i punti vicini a casa sua.
        "lat": props.get("lat"),
        "lon": props.get("lon"),
    }


def suggest(query: str) -> List[Dict[str, str]]:
    """Suggerimenti per `query`. Lista vuota se la chiave manca o se Geoapify
    non risponde: un fornitore giu' non deve impedire di comprare."""
    text = (query or "").strip()
    if len(text) < 3:
        return []
    key = _api_key()
    if not key:
        return []

    params = {
        "text": text,
        "filter": f"countrycode:{_country_filter()}",
        "limit": MAX_RESULTS,
        "lang": "it",
        "format": "geojson",
        "apiKey": key,
    }
    try:
        resp = requests.get(API_URL, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as exc:
        LOGGER.warning("Geoapify non raggiungibile: %s", exc)
        return []
    except ValueError as exc:
        LOGGER.warning("Geoapify ha risposto con JSON non valido: %s", exc)
        return []

    features = payload.get("features") or []
    out: List[Dict[str, str]] = []
    for feature in features[:MAX_RESULTS]:
        suggestion = _to_suggestion(feature)
        # Scartiamo i risultati senza via (citta', comuni, regioni): questo
        # campo e' "via e numero civico", e un suggerimento tipo "Livorno,
        # Toscana, Italia" non ha niente da metterci dentro. Offrirlo porta
        # solo a ritrovarsi la citta' scritta nel campo dell'indirizzo.
        if suggestion["label"] and suggestion["street"]:
            out.append(suggestion)
    return out
