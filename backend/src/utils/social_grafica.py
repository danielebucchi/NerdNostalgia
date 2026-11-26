"""
Lo stile delle grafiche social, lo stesso del sito e del logo: sfondo
pastello rosa → lilla con stelline, foto dentro una carta bianca con
ombra, il logo come bollino, etichette colorate e il prezzo in una pillola
rosa. Titoli in Fredoka, testi in Manrope (assets/fonts, licenza OFL).

Usato dai post, dalle Storie, dai caroselli delle rubriche e dai Reel
(utils/instagram, instagram_rubriche, instagram_reel).
"""
import random
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ASSETS = Path(__file__).resolve().parent.parent / "assets"

INK = (61, 42, 92)
INK_SOFT = (107, 91, 138)
ROSA = (248, 168, 200)
ROSA_FORTE = (232, 121, 168)
LILLA = (212, 196, 240)
LILLA_FORTE = (168, 144, 216)
MENTA = (168, 230, 212)
CIELO = (184, 224, 232)
BIANCO = (255, 255, 255)

Colore = Tuple[int, int, int]


@lru_cache(maxsize=64)
def font(nome: str, size: int, peso: str = "Bold") -> ImageFont.FreeTypeFont:
    """"titolo" = Fredoka, "testo" = Manrope; se mancano, quello di sistema."""
    file = ASSETS / "fonts" / ("Fredoka.ttf" if nome == "titolo" else "Manrope.ttf")
    try:
        f = ImageFont.truetype(str(file), size)
        try:
            f.set_variation_by_name(peso)
        except (OSError, ValueError):
            pass
        return f
    except OSError:
        from utils import instagram
        return instagram._font(size)


# ---------------------------------------------------------------------------
# Sfondo
# ---------------------------------------------------------------------------

def _stella(draw: ImageDraw.ImageDraw, x: float, y: float, r: float, colore) -> None:
    """Una stellina a quattro punte, come quelle del logo."""
    p = r * 0.28
    draw.polygon([(x, y - r), (x + p, y - p), (x + r, y), (x + p, y + p),
                  (x, y + r), (x - p, y + p), (x - r, y), (x - p, y - p)], fill=colore)


def sfondo(misure: Tuple[int, int], seme: int = 0, colori: Sequence[Colore] = (ROSA, LILLA, CIELO)) -> Image.Image:
    """Sfumatura diagonale pastello con qualche stellina e qualche puntino."""
    w, h = misure
    piccola = Image.new("RGB", (64, 64))
    px = piccola.load()
    for yy in range(64):
        for xx in range(64):
            t = (xx + yy) / 126
            if t < 0.5:
                a, b, k = colori[0], colori[1], t / 0.5
            else:
                a, b, k = colori[1], colori[2], (t - 0.5) / 0.5
            px[xx, yy] = tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))
    tela = piccola.resize((w, h), Image.BICUBIC).convert("RGBA")
    velo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(velo)
    caso = random.Random(seme)
    for _ in range(14):
        _stella(draw, caso.uniform(0, w), caso.uniform(0, h), caso.uniform(10, 26), (255, 255, 255, 170))
    for _ in range(40):
        x, y, r = caso.uniform(0, w), caso.uniform(0, h), caso.uniform(2, 5)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 130))
    return Image.alpha_composite(tela, velo)


# ---------------------------------------------------------------------------
# Elementi
# ---------------------------------------------------------------------------

@lru_cache(maxsize=8)
def _logo(diametro: int) -> Optional[Image.Image]:
    """Il cerchio del logo, senza l'alone nero del file originale."""
    file = ASSETS / "logo.png"
    if not file.exists():
        return None
    logo = Image.open(file).convert("RGBA")
    cx, cy, r = logo.width // 2, logo.height // 2, int(logo.width * 0.372)
    logo = logo.crop((cx - r, cy - r, cx + r, cy + r))
    maschera = Image.new("L", logo.size, 0)
    ImageDraw.Draw(maschera).ellipse((0, 0, logo.width - 1, logo.height - 1), fill=255)
    logo.putalpha(maschera)
    return logo.resize((diametro, diametro), Image.LANCZOS)


def logo(tela: Image.Image, x: int, y: int, diametro: int) -> None:
    img = _logo(diametro)
    if img is None:
        return
    ombra = Image.new("RGBA", tela.size, (0, 0, 0, 0))
    ImageDraw.Draw(ombra).ellipse((x + 4, y + 10, x + diametro + 4, y + diametro + 10), fill=(61, 42, 92, 70))
    tela.alpha_composite(ombra.filter(ImageFilter.GaussianBlur(10)))
    tela.alpha_composite(img, (x, y))


def carta(tela: Image.Image, foto: Optional[Image.Image], box: Tuple[int, int, int, int],
          margine: int = 22, raggio: int = 36, inclinazione: float = 0.0) -> None:
    """La foto dentro una carta bianca arrotondata con ombra, centrata nel box
    (x0, y0, x1, y1) e grande quanto ci sta."""
    x0, y0, x1, y1 = box
    if foto is None:
        foto = Image.new("RGB", (600, 800), LILLA)
    spazio_w, spazio_h = x1 - x0 - 2 * margine, y1 - y0 - 2 * margine
    scala = min(spazio_w / foto.width, spazio_h / foto.height)
    fw, fh = max(1, round(foto.width * scala)), max(1, round(foto.height * scala))
    foto = foto.convert("RGB").resize((fw, fh), Image.LANCZOS)
    cw, ch = fw + 2 * margine, fh + 2 * margine
    pezzo = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    ImageDraw.Draw(pezzo).rounded_rectangle((0, 0, cw - 1, ch - 1), radius=raggio, fill=BIANCO + (255,))
    maschera = Image.new("L", (fw, fh), 0)
    ImageDraw.Draw(maschera).rounded_rectangle((0, 0, fw - 1, fh - 1), radius=max(6, raggio - margine // 2), fill=255)
    pezzo.paste(foto, (margine, margine), maschera)
    if inclinazione:
        pezzo = pezzo.rotate(inclinazione, expand=True, resample=Image.BICUBIC)
    px = x0 + (x1 - x0 - pezzo.width) // 2
    py = y0 + (y1 - y0 - pezzo.height) // 2
    ombra = Image.new("RGBA", tela.size, (0, 0, 0, 0))
    ombra.paste((61, 42, 92, 80), (px + 10, py + 22), pezzo.split()[3])
    tela.alpha_composite(ombra.filter(ImageFilter.GaussianBlur(22)))
    tela.alpha_composite(pezzo, (px, py))


def pillola(tela: Image.Image, testo: str, centro_x: int, y: int, size: int = 72,
            sfondo_colore: Colore = ROSA_FORTE, colore: Colore = BIANCO, nome_font: str = "titolo") -> int:
    """Testo dentro una pillola colorata, centrata su centro_x. Torna la y sotto."""
    draw = ImageDraw.Draw(tela)
    f = font(nome_font, size)
    sx, sy = int(size * 0.55), int(size * 0.28)
    l, t, r, b = draw.textbbox((0, 0), testo, font=f)
    w, h = r - l, b - t
    x0, y0 = centro_x - w // 2 - sx, y
    x1, y1 = centro_x + w // 2 + sx, y + h + 2 * sy
    ombra = Image.new("RGBA", tela.size, (0, 0, 0, 0))
    ImageDraw.Draw(ombra).rounded_rectangle((x0 + 3, y0 + 10, x1 + 3, y1 + 10), radius=(y1 - y0) // 2,
                                            fill=sfondo_colore + (110,))
    tela.alpha_composite(ombra.filter(ImageFilter.GaussianBlur(12)))
    draw = ImageDraw.Draw(tela)
    draw.rounded_rectangle((x0, y0, x1, y1), radius=(y1 - y0) // 2, fill=sfondo_colore)
    draw.text((x0 + sx - l, y0 + sy - t), testo, font=f, fill=colore)
    return y1


def etichetta(tela: Image.Image, testo: str, x: int, y: int, colore: Colore = BIANCO,
              testo_colore: Colore = INK, size: int = 34, allinea: str = "sinistra") -> None:
    """Una piccola etichetta arrotondata (categoria, "SCORRI →"...). `x` e' il
    bordo sinistro, il destro o il centro secondo `allinea`."""
    draw = ImageDraw.Draw(tela)
    f = font("testo", size, "ExtraBold")
    l, t, r, b = draw.textbbox((0, 0), testo, font=f)
    w, h = r - l + 2 * 26, b - t + 2 * 14
    if allinea == "destra":
        x -= w
    elif allinea == "centro":
        x -= w // 2
    draw.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=colore)
    draw.text((x + 26 - l, y + 14 - t), testo, font=f, fill=testo_colore)


def testo_centrato(tela: Image.Image, testo: str, y: int, nome_font: str, size: int, colore: Colore,
                   righe_max: int = 2, larghezza: Optional[int] = None, peso: str = "Bold",
                   interlinea: int = 10) -> int:
    """Testo a capo su piu' righe, centrato. Torna la y sotto l'ultima riga."""
    from utils import instagram
    draw = ImageDraw.Draw(tela)
    f = font(nome_font, size, peso)
    larghezza = larghezza or tela.width - 140
    for riga in instagram._righe(draw, testo, f, larghezza, righe_max):
        draw.text(((tela.width - draw.textlength(riga, font=f)) / 2, y), riga, font=f, fill=colore)
        y += size + interlinea
    return y


def mosaico(tela: Image.Image, foto: List[Optional[Image.Image]], box: Tuple[int, int, int, int]) -> None:
    """Fino a quattro foto in carte leggermente inclinate, come un mazzo sul tavolo."""
    x0, y0, x1, y1 = box
    foto = [f for f in foto if f is not None][:4]
    if not foto:
        return
    if len(foto) == 1:
        carta(tela, foto[0], box, inclinazione=-3)
        return
    meta_w, meta_h = (x1 - x0) // 2, (y1 - y0) // 2
    posti = [(x0, y0), (x0 + meta_w, y0), (x0, y0 + meta_h), (x0 + meta_w, y0 + meta_h)]
    if len(foto) <= 2:
        posti = [(x0, y0 + meta_h // 2), (x0 + meta_w, y0 + meta_h // 2)]
    angoli = [-5, 4, 3, -4]
    for i, (f, (px, py)) in enumerate(zip(foto, posti)):
        carta(tela, f, (px, py, px + meta_w, py + meta_h), margine=14, raggio=24, inclinazione=angoli[i])


def finale(misure: Tuple[int, int], seme: int = 0) -> Image.Image:
    """L'ultima slide: l'invito a commentare LISTA e il link in bio."""
    w, h = misure
    tela = sfondo(misure, seme, (LILLA, ROSA, MENTA))
    logo(tela, (w - 260) // 2, int(h * 0.14), 260)
    y = int(h * 0.14) + 320
    y = testo_centrato(tela, "Ti piace qualcosa?", y, "titolo", 92, INK, 2)
    y = testo_centrato(tela, "Commenta", y + 30, "testo", 52, INK_SOFT, 1, peso="SemiBold")
    y = pillola(tela, "LISTA", w // 2, y + 10, 110)
    y = testo_centrato(tela, "e ti mandiamo in privato i link di tutti i pezzi", y + 40, "testo", 46, INK, 3,
                       larghezza=w - 220, peso="SemiBold")
    etichetta(tela, "nerdnostalgia.store · link in bio", w // 2, h - 140, BIANCO, INK, 34, "centro")
    return tela.convert("RGB")
