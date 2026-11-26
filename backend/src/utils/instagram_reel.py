"""
Il Reel del mese: cosa abbiamo venduto.

Il primo del mese alle 18:00 un video verticale con i pezzi venduti nel mese
prima (i piu' cari per primi, al massimo MAX_PEZZI), ognuno con il timbro
VENDUTO, su una musichetta 8-bit originale (utils/chiptune.py: niente
brani di terzi, Instagram non lo silenzia). Un Reel al mese, solo se c'e'
qualcosa da mostrare e solo se Instagram e' acceso.

Il video si monta con il ffmpeg di imageio-ffmpeg (incluso nel pacchetto,
niente da installare nel container) e Instagram lo scarica da /static/social/.
"""
import io
import logging
import math
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw
from sqlalchemy.orm import Session

from models.db import Article, ArticleStatus
from utils import chiptune, instagram

LOGGER = logging.getLogger("instagram_reel")

MAX_PEZZI = 20
INTRO = 2.5
PER_PEZZO = 1.4
OUTRO = 3.0
FPS = 30
CHIAVE_ULTIMO = "instagram_reel_last"

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
        "agosto", "settembre", "ottobre", "novembre", "dicembre"]


def mese_precedente(oggi: Optional[datetime] = None) -> Tuple[int, int]:
    oggi = oggi or datetime.now()
    return (oggi.year - 1, 12) if oggi.month == 1 else (oggi.year, oggi.month - 1)


def venduti(db: Session, anno: int, mese: int) -> List[Article]:
    inizio = datetime(anno, mese, 1)
    fine = datetime(anno + (mese == 12), mese % 12 + 1, 1)
    articoli = (db.query(Article)
                .filter(Article.status == ArticleStatus.SOLD,
                        Article.sold_at >= inizio, Article.sold_at < fine)
                .all())
    articoli = [a for a in articoli if a.images]
    articoli.sort(key=lambda a: float(a.price or 0), reverse=True)
    return articoli


# ---------------------------------------------------------------------------
# Fotogrammi
# ---------------------------------------------------------------------------

def _intro(anno: int, mese: int, quanti: int, articoli: Optional[List[Article]] = None) -> Image.Image:
    from utils import instagram_rubriche
    return instagram_rubriche.copertina(f"Venduti a {MESI[mese - 1]}",
                                        f"{quanti} pezz{'o' if quanti == 1 else 'i'} hanno trovato casa",
                                        instagram.STORIA, "GRAZIE A VOI", articoli=articoli)


def _pezzo(article: Article, n: int, totale: int) -> Image.Image:
    from utils import social_grafica as g
    w, h = instagram.STORIA
    tela = g.sfondo((w, h), seme=article.id or n)
    g.logo(tela, 60, 70, 150)
    g.etichetta(tela, f"{n}/{totale}", w - 60, 110, g.BIANCO, g.INK, 40, "destra")
    g.carta(tela, instagram._foto(article), (90, 260, w - 90, 1420))
    # Il timbro VENDUTO, inclinato sopra la foto.
    timbro = Image.new("RGBA", (780, 220), (0, 0, 0, 0))
    td = ImageDraw.Draw(timbro)
    td.rounded_rectangle((8, 8, 772, 212), radius=40, fill=(255, 255, 255, 215),
                         outline=g.ROSA_FORTE + (255,), width=14)
    f = g.font("titolo", 130)
    td.text(((780 - td.textlength("VENDUTO", font=f)) / 2, 28), "VENDUTO", font=f, fill=g.ROSA_FORTE + (255,))
    timbro = timbro.rotate(12, expand=True, resample=Image.BICUBIC)
    tela.alpha_composite(timbro, ((w - timbro.width) // 2, 700))
    g.testo_centrato(tela, article.title or "", 1490, "titolo", 58, g.INK, 3)
    g.etichetta(tela, "nerdnostalgia.store", w // 2, h - 140, g.BIANCO, g.INK, 40, "centro")
    return tela.convert("RGB")


def _outro() -> Image.Image:
    from utils import social_grafica as g
    w, h = instagram.STORIA
    tela = g.sfondo((w, h), seme=7, colori=(g.LILLA, g.ROSA, g.MENTA))
    g.logo(tela, (w - 320) // 2, 380, 320)
    y = g.testo_centrato(tela, "Grazie!", 760, "titolo", 150, g.INK, 1)
    y = g.testo_centrato(tela, "Ogni giorno nuovi arrivi", y + 20, "testo", 58, g.INK_SOFT, 2, peso="SemiBold")
    g.pillola(tela, "nerdnostalgia.store", w // 2, y + 50, 70)
    g.etichetta(tela, "link in bio", w // 2, h - 200, g.BIANCO, g.INK, 44, "centro")
    return tela.convert("RGB")


# ---------------------------------------------------------------------------
# Video
# ---------------------------------------------------------------------------

def video(articoli: List[Article], anno: int, mese: int) -> bytes:
    """Il Reel dei venduti del mese."""
    pezzi = articoli[:MAX_PEZZI]
    slide = [(_intro(anno, mese, len(articoli), pezzi), INTRO)]
    slide += [(_pezzo(a, i + 1, len(pezzi)), PER_PEZZO) for i, a in enumerate(pezzi)]
    slide.append((_outro(), OUTRO))
    return monta(slide, seme=anno * 100 + mese)


def monta(slide: List[Tuple[Image.Image, float]], seme: int) -> bytes:
    """L'MP4 di un Reel da una sequenza di immagini 1080x1920 con la loro
    durata, sulla musichetta 8-bit `seme`: H.264 + AAC, come lo vuole Instagram."""
    import imageio_ffmpeg
    durata = sum(d for _, d in slide)
    with tempfile.TemporaryDirectory() as cartella:
        tmp = Path(cartella)
        elenco = []
        for i, (img, d) in enumerate(slide):
            percorso = tmp / f"s{i:03d}.png"
            img.save(percorso)
            elenco.append(f"file '{percorso}'\nduration {d}")
        # Il concat di ffmpeg vuole l'ultima immagine ripetuta, o ne ignora la durata.
        elenco.append(f"file '{tmp / f's{len(slide) - 1:03d}.png'}'")
        (tmp / "elenco.txt").write_text("\n".join(elenco))
        (tmp / "musica.wav").write_bytes(chiptune.musica(math.ceil(durata), seme=seme))
        uscita = tmp / "reel.mp4"
        subprocess.run(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
             "-f", "concat", "-safe", "0", "-i", str(tmp / "elenco.txt"),
             "-i", str(tmp / "musica.wav"),
             "-vf", f"fps={FPS},format=yuv420p", "-c:v", "libx264", "-preset", "medium",
             "-profile:v", "high", "-crf", "21",
             "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
             "-t", f"{durata:.2f}", "-movflags", "+faststart", str(uscita)],
            check=True, timeout=600,
        )
        return uscita.read_bytes()


def didascalia(articoli: List[Article], mese: int) -> str:
    quanti = len(articoli)
    righe = [f"📦 Venduti a {MESI[mese - 1]}: {quanti} pezz{'o' if quanti == 1 else 'i'} hanno trovato una nuova casa!",
             "", "Grazie a tutti quelli che hanno comprato da noi 💜",
             "", "🛒 Ogni giorno nuovi arrivi su nerdnostalgia.store (link in bio)",
             f"💬 Le novità in tempo reale nel gruppo Telegram: {instagram.TELEGRAM_URL}",
             "", instagram._hashtag(articoli[:MAX_PEZZI])]
    return "\n".join(righe)[:2200]


def _salva(contenuto: bytes, anno: int, mese: int) -> str:
    return salva(contenuto, f"reel-{anno}-{mese:02d}")


def salva(contenuto: bytes, nome: str, estensione: str = "mp4") -> str:
    """Salva un file tra quelli statici e ne torna l'URL pubblico: Instagram
    scarica da li' video e immagini."""
    from utils.storage import UPLOADS_DIR
    cartella = UPLOADS_DIR / "social"
    cartella.mkdir(parents=True, exist_ok=True)
    (cartella / f"{nome}.{estensione}").write_bytes(contenuto)
    return f"{instagram._api_url()}/static/social/{nome}.{estensione}"


def anteprima(db: Session, anno: int, mese: int) -> Optional[Dict[str, object]]:
    """Monta il Reel senza pubblicarlo: per guardarlo prima."""
    articoli = venduti(db, anno, mese)
    if not articoli:
        return None
    url = _salva(video(articoli, anno, mese), anno, mese)
    return {"video": url, "articoli": len(articoli), "caption": didascalia(articoli, mese)}


def pubblica(db: Session, anno: Optional[int] = None, mese: Optional[int] = None,
             forza: bool = False) -> Optional[Dict[str, object]]:
    """Il Reel del mese (di default quello appena finito). Una volta sola per
    mese, salvo `forza`. None se spento o senza venduti."""
    if not instagram.acceso(db):
        return None
    if anno is None or mese is None:
        anno, mese = mese_precedente()
    chiave = f"{anno}-{mese:02d}"
    impostazioni = instagram._impostazioni(db)
    if not forza and impostazioni.get_value(CHIAVE_ULTIMO, default="") == chiave:
        return None
    articoli = venduti(db, anno, mese)
    if not articoli:
        return None
    url = _salva(video(articoli, anno, mese), anno, mese)
    token = instagram._token(db)
    contenitore = instagram._contenitore(token, media_type="REELS", video_url=url,
                                         caption=didascalia(articoli, mese), share_to_feed="true")
    # Un video Instagram lo elabora con calma: fino a 5 minuti.
    instagram._attendi(token, contenitore, tentativi=60, pausa=5.0)
    media = instagram._pubblica(token, contenitore)
    impostazioni.upsert(CHIAVE_ULTIMO, chiave)
    from utils import instagram_stats
    instagram_stats.registra(db, media, "reel", didascalia(articoli, mese), n_items=len(articoli))
    LOGGER.info("Instagram: Reel %s dei venduti di %s (%d pezzi)", media, chiave, len(articoli))
    return {"media": media, "mese": chiave, "articoli": len(articoli)}
