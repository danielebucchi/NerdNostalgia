"""
Cio' che lo scan dice oltre a "quale carta e'": reverse/foil, prima
edizione, condizione.

Il trucco comune e' il CONFRONTO con l'immagine CardTrader della stessa
carta. Uno scan e un'immagine ufficiale non sono mai uguali (scanner,
colori, nitidezza), ma lo sono le PROPORZIONI fra zone della stessa carta:

- reverse/foil: la lucidatura allo scanner esce come una grana fitta.
  In un reverse Pokemon e' su tutta la carta TRANNE l'illustrazione, in
  un foil Magic dappertutto: in entrambi i casi la zona di testo (piatta
  in una carta normale) diventa granulosa. Si misura la grana del testo
  rispetto a quella dell'illustrazione, sullo scan e sull'immagine
  ufficiale: se sullo scan il rapporto e' molto piu' alto, e' lucida.
- prima edizione Pokemon: il timbro nero "Edition 1" sotto l'angolo
  sinistro dell'illustrazione. Si contano i pixel scuri in quella zona,
  sullo scan e sull'ufficiale (che e' quasi sempre l'unlimited).
- prima edizione Yu-Gi-Oh!: c'e' scritto ("1st Edition"), basta l'OCR.
- condizione: centratura (spessore dei bordi) e sbiancamento lungo i
  bordi e sugli angoli, meglio ancora se c'e' anche il retro, dove
  l'usura si vede di piu'. Pieghe e graffi sulla superficie NO: da uno
  scan non si distinguono in modo affidabile dai riflessi.

Sono STIME: ogni valore torna con la misura che l'ha prodotto, e quando
la misura cade nella zona grigia il valore e' None ("non so"), non un
tiro a indovinare. La conferma resta a una persona.

Le soglie sono tarate su poche carte: vanno riviste con gli scan veri
(vedi SOGLIE).
"""
import io
import logging
import re
from typing import Any, Dict, Optional, Tuple

import requests
from PIL import Image, ImageChops, ImageFilter, ImageOps, ImageStat

LOGGER = logging.getLogger("card_features")

# Dimensione comune per i confronti
W, H = 500, 700

# Zone della carta in frazioni (x0, y0, x1, y1). Le carte di un gioco
# hanno tutte lo stesso impaginato, abbastanza da usare zone fisse.
ZONE = {
    "pokemon": {"arte": (0.10, 0.11, 0.90, 0.50), "testo": (0.08, 0.58, 0.92, 0.86),
                "timbro": (0.03, 0.47, 0.24, 0.60)},
    "magic": {"arte": (0.09, 0.12, 0.91, 0.55), "testo": (0.09, 0.63, 0.91, 0.88)},
    "yugioh": {"arte": (0.13, 0.19, 0.87, 0.68), "testo": (0.08, 0.76, 0.92, 0.92)},
    "onepiece": {"arte": (0.08, 0.08, 0.92, 0.60), "testo": (0.08, 0.65, 0.92, 0.90)},
}

SOGLIE = {
    # grana testo/arte dello scan diviso quella dell'ufficiale
    "foil_si": 1.6,
    "foil_no": 1.2,
    # quota di pixel scuri in piu' nella zona del timbro
    "timbro_si": 0.035,
    "timbro_no": 0.012,
    # quota di pixel sbiancati nella fascia dei bordi → condizione
    "usura": [(0.008, "Near Mint"), (0.025, "Slightly Played"),
              (0.06, "Moderately Played"), (0.12, "Played")],
}

RE_PRIMA_EDIZIONE = re.compile(
    r"1\s*st\s*edition|1\s*[aª°]\s*edizione|1\.\s*auflage|1\s*re\s*[ée]dition|1\s*[ªa]\s*edici[oó]n",
    re.I,
)


def _norm(img: Image.Image) -> Image.Image:
    return img.convert("RGB").resize((W, H), Image.LANCZOS)


def _zona(img: Image.Image, frazioni: Tuple[float, float, float, float]) -> Image.Image:
    x0, y0, x1, y1 = frazioni
    return img.crop((int(x0 * img.width), int(y0 * img.height),
                     int(x1 * img.width), int(y1 * img.height)))


def grana(img: Image.Image) -> float:
    """Energia ad alta frequenza: quanto l'immagine si discosta da se'
    stessa sfocata. Piatto → ~0, granuloso → alto."""
    g = img.convert("L")
    diff = ImageChops.difference(g, g.filter(ImageFilter.GaussianBlur(2)))
    return ImageStat.Stat(diff).mean[0]


def download_reference(url: Optional[str]) -> Optional[Image.Image]:
    """Immagine CardTrader grande (la "show"): il timbro della prima
    edizione nell'anteprima e' di pochi pixel."""
    if not url:
        return None
    try:
        resp = requests.get(url.replace("/preview_", "/show_"), timeout=15)
        resp.raise_for_status()
        with Image.open(io.BytesIO(resp.content)) as im:
            return im.convert("RGB")
    except Exception as exc:  # noqa: BLE001
        LOGGER.info("Immagine di riferimento %s non scaricata: %s", url, exc)
        return None


# ── Reverse / foil ────────────────────────────────────────────────

def foil(scan: Image.Image, ref: Optional[Image.Image], gioco: str) -> Dict[str, Any]:
    zone = ZONE.get(gioco)
    if not zone or ref is None:
        return {"value": None, "reason": "nessun riferimento"}
    # Alla risoluzione dell'immagine ufficiale (la piu' piccola delle due):
    # portare entrambe a una misura fissa sotto quella cancellerebbe la
    # grana del foil nella media dei pixel.
    r = ref.convert("RGB")
    s = scan.convert("RGB").resize(r.size, Image.LANCZOS)

    def rapporto(img):
        arte = grana(_zona(img, zone["arte"]))
        return grana(_zona(img, zone["testo"])) / max(arte, 0.5)

    if gioco == "pokemon":
        # Reverse: lucida fuori dall'illustrazione, non dentro.
        misura = rapporto(s) / max(rapporto(r), 0.05)
    else:
        # Foil Magic & co.: lucida dappertutto, il rapporto fra zone non
        # cambia. Si guarda la grana del riquadro di testo e basta.
        misura = grana(_zona(s, zone["testo"])) / max(grana(_zona(r, zone["testo"])), 0.5)
    if misura >= SOGLIE["foil_si"]:
        valore = True
    elif misura <= SOGLIE["foil_no"]:
        valore = False
    else:
        valore = None
    return {"value": valore, "score": round(misura, 2)}


# ── Prima edizione ────────────────────────────────────────────────

def _quota_scura(img: Image.Image) -> float:
    g = img.convert("L")
    scuri = sum(g.histogram()[:60])
    return scuri / max(g.width * g.height, 1)


def first_edition(
    scan: Image.Image, ref: Optional[Image.Image], gioco: str, testo_ocr: str,
) -> Dict[str, Any]:
    if gioco == "yugioh":
        trovato = bool(RE_PRIMA_EDIZIONE.search(testo_ocr or ""))
        # "1st Edition" assente dall'OCR puo' anche essere letto male: si
        # dice no, ma senza la certezza del si'.
        return {"value": trovato, "reason": "scritta letta" if trovato else "scritta non trovata"}
    if gioco == "pokemon":
        if ref is None:
            return {"value": None, "reason": "nessun riferimento"}
        zona = ZONE["pokemon"]["timbro"]
        diff = _quota_scura(_zona(_norm(scan), zona)) - _quota_scura(_zona(_norm(ref), zona))
        if diff >= SOGLIE["timbro_si"]:
            valore = True
        elif diff <= SOGLIE["timbro_no"]:
            valore = False
        else:
            valore = None
        return {"value": valore, "score": round(diff, 3)}
    return {"value": None, "reason": "non prevista per questo gioco"}


# ── Condizione ────────────────────────────────────────────────────

def _lum(px) -> float:
    r, g, b = px[:3]
    return 0.299 * r + 0.587 * g + 0.114 * b


def _dist(a, b) -> float:
    return sum((x - y) ** 2 for x, y in zip(a[:3], b[:3])) ** 0.5


def _verso_il_bianco(p, colore) -> float:
    """Distanza di p dal segmento colore→bianco."""
    a = [float(x) for x in colore[:3]]
    d = [255.0 - x for x in a]
    dd = sum(x * x for x in d) or 1.0
    t = max(0.0, min(1.0, sum((p[i] - a[i]) * d[i] for i in range(3)) / dd))
    return sum((p[i] - (a[i] + t * d[i])) ** 2 for i in range(3)) ** 0.5


def _bordo(img: Image.Image, lato: str) -> Optional[float]:
    """Spessore del bordo esterno su un lato, in frazione della carta:
    da fuori verso dentro, dove il colore smette di essere quello del
    bordo. Mediana su piu' linee, per non farsi ingannare da una scritta."""
    px = img.load()
    w, h = img.size
    misure = []
    for k in range(20, 81, 4):
        if lato in ("sx", "dx"):
            y = h * k // 100
            passi = [(x, y) for x in range(w // 2)] if lato == "sx" else \
                [(w - 1 - x, y) for x in range(w // 2)]
        else:
            x = w * k // 100
            passi = [(x, y) for y in range(h // 2)] if lato == "su" else \
                [(x, h - 1 - y) for y in range(h // 2)]
        # colore del bordo: un po' dentro dal taglio (il taglio puo'
        # includere un filo di piano dello scanner)
        base = px[passi[4]]
        for i, p in enumerate(passi[4:], start=4):
            if _dist(px[p], base) > 70:
                misure.append(i)
                break
    if len(misure) < 5:
        return None
    misure.sort()
    mediana = misure[len(misure) // 2]
    dim = w if lato in ("sx", "dx") else h
    frazione = mediana / dim
    return frazione if 0.01 <= frazione <= 0.15 else None


def centratura(img: Image.Image) -> Dict[str, Any]:
    s = _norm(img)
    sx, dx, su, giu = (_bordo(s, lato) for lato in ("sx", "dx", "su", "giu"))
    out: Dict[str, Any] = {}
    if sx and dx:
        out["lr"] = round(100 * sx / (sx + dx))
    if su and giu:
        out["tb"] = round(100 * su / (su + giu))
    return out


def usura(img: Image.Image) -> Optional[float]:
    """Quota di pixel sbiancati nella fascia lungo i bordi (angoli
    compresi, ma senza la parte fuori dall'angolo arrotondato, che e'
    piano dello scanner). None se il bordo e' gia' bianco: li' lo
    sbiancamento non si vede."""
    s = _norm(img)
    px = s.load()
    fascia = int(W * 0.025)
    salto = 2  # il filo esterno puo' essere piano dello scanner
    raggio = int(W * 0.048)

    def bianco(p):
        return _lum(p) > 185 and max(p[:3]) - min(p[:3]) < 40

    campioni = [px[x, y] for x in range(salto + 2, fascia, 2) for y in range(H // 4, 3 * H // 4, 7)]
    # Se la fascia e' bianca per la maggior parte, il bordo E' bianco
    # (One Piece, Magic moderni): lo sbiancamento non si distingue.
    if sum(1 for c in campioni if bianco(c)) > len(campioni) / 2:
        return None
    # Il colore del bordo lo dicono i pixel NON sbiancati: su una carta
    # molto usurata il bianco non deve passare per il colore del bordo.
    colorati = sorted((c for c in campioni if not bianco(c)), key=_lum) or sorted(campioni, key=_lum)
    colore = colorati[len(colorati) // 2]
    # Il bordo dev'essere di un colore solo: con l'arte fino al taglio
    # (borderless, full art) i chiari dell'illustrazione sembrerebbero
    # usura. Li' non si misura.
    # Conta come bordo anche il colore del bordo schiarito verso il bianco:
    # e' il contorno sfumato dello sbiancamento, non un'illustrazione.
    uniformi = sum(1 for c in campioni if _verso_il_bianco(c, colore) < 40) / len(campioni)
    if uniformi < 0.8:
        return None
    # Bordo bianco (o quasi): lo sbiancamento non si distingue. Il giallo
    # dei Pokemon e' chiaro ma saturo, e li' invece si vede benissimo.
    if _lum(colore) > 215 and max(colore[:3]) - min(colore[:3]) < 40:
        return None

    def fuori_dall_angolo(x, y):
        cx = raggio if x < raggio else (W - 1 - raggio if x > W - 1 - raggio else None)
        cy = raggio if y < raggio else (H - 1 - raggio if y > H - 1 - raggio else None)
        if cx is None or cy is None:
            return False
        return (x - cx) ** 2 + (y - cy) ** 2 > raggio ** 2

    tot = bianchi = 0
    for y in range(salto, H - salto):
        xs = range(salto, W - salto) if (y < fascia or y >= H - fascia) else \
            list(range(salto, fascia)) + list(range(W - fascia, W - salto))
        for x in xs:
            if fuori_dall_angolo(x, y):
                continue
            tot += 1
            p = px[x, y]
            # sbiancato = chiaro e poco saturo (il giallo chiaro del bordo
            # Pokemon non conta)
            if bianco(p) and _dist(p, colore) > 60:
                bianchi += 1
    return bianchi / max(tot, 1)


def condition(fronte: Image.Image, retro: Optional[Image.Image] = None) -> Dict[str, Any]:
    """Stima della condizione CardTrader dall'usura dei bordi. Mai "Mint":
    da uno scan non lo si puo' garantire."""
    u_fronte = usura(fronte)
    u_retro = usura(retro) if retro is not None else None
    misure = [u for u in (u_fronte, u_retro) if u is not None]
    out: Dict[str, Any] = {
        "centering": centratura(fronte),
        "wear_front": round(u_fronte, 4) if u_fronte is not None else None,
        "wear_back": round(u_retro, 4) if u_retro is not None else None,
        "value": None,
    }
    if not misure:
        out["reason"] = "bordo bianco o senza bordo (arte fino al taglio): usura non misurabile"
        return out
    peggiore = max(misure)
    out["value"] = next((c for limite, c in SOGLIE["usura"] if peggiore < limite), "Poor")
    if retro is None:
        out["reason"] = "solo fronte: col retro la stima e' piu' affidabile"
    return out


# ── Tutto insieme ─────────────────────────────────────────────────

def analyze(
    scan: Image.Image,
    gioco: Optional[str],
    editable: str,
    reference_url: Optional[str],
    testo_ocr: str = "",
    retro: Optional[Image.Image] = None,
) -> Dict[str, Any]:
    """Analisi completa per la carta scelta. `editable` = attributi che
    CardTrader ammette per lei: se non ammette il reverse, non lo si
    cerca (e non lo si propone)."""
    props = {p.split(":")[0] for p in (editable or "").split(",") if p}
    ha_foil = any(p.endswith("_reverse") or p.endswith("_foil") for p in props)
    ha_prima = "first_edition" in props
    ref = download_reference(reference_url) if (ha_foil or ha_prima) else None

    out: Dict[str, Any] = {
        "supports": {"reverse": ha_foil, "first_edition": ha_prima},
        "condition": condition(scan, retro),
    }
    out["reverse"] = foil(scan, ref, gioco or "") if ha_foil else {"value": False, "reason": "non prevista"}
    out["first_edition"] = (
        first_edition(scan, ref, gioco or "", testo_ocr) if ha_prima
        else {"value": False, "reason": "non prevista"}
    )
    return out
