"""
Musichetta 8-bit originale per i Reel.

Generata da zero ogni volta (nessun brano di terzi, quindi niente problemi
di copyright su Instagram): una melodia a onda quadra su una progressione
di accordi, basso a onda triangolare e charleston di rumore, come le
colonne sonore delle console a 8 bit. Il `seme` cambia la melodia: ogni
mese un motivo diverso, sempre riproducibile.
"""
import io
import math
import random
import struct
import wave

FREQ = 22050
BPM = 132

# Scala di Do maggiore su due ottave (semitoni da Do4) e progressioni allegre.
SCALA = [0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19, 21, 23, 24]
PROGRESSIONI = [
    [0, 7, 9, 5],    # I  V  vi IV
    [0, 5, 7, 7],    # I  IV V  V
    [9, 5, 0, 7],    # vi IV I  V
    [0, 9, 5, 7],    # I  vi IV V
]
TRIADE = [0, 4, 7]
TRIADE_MINORE = [0, 3, 7]


def _nota(semitoni: int, ottava: int = 4) -> float:
    return 261.63 * 2 ** ((semitoni + 12 * (ottava - 4)) / 12)


def _quadra(f: float, t: float, duty: float = 0.5) -> float:
    return 1.0 if (f * t) % 1.0 < duty else -1.0


def _triangolo(f: float, t: float) -> float:
    fase = (f * t) % 1.0
    return 4 * fase - 1 if fase < 0.5 else 3 - 4 * fase


def _accordo(radice: int) -> list:
    return [radice + i for i in (TRIADE_MINORE if radice in (9, 2, 4) else TRIADE)]


def musica(secondi: float, seme: int = 0) -> bytes:
    """WAV mono 16 bit di `secondi` secondi, con dissolvenza finale."""
    caso = random.Random(seme)
    progressione = caso.choice(PROGRESSIONI)
    sedicesimo = 60 / BPM / 4
    battute = math.ceil(secondi / (sedicesimo * 16))

    # Melodia: per ogni battuta un motivo di 16 sedicesimi costruito sulle
    # note dell'accordo, con qualche nota di passaggio e qualche pausa.
    motivo_base = [caso.choice([0, 1, 2, None, 0, 2]) for _ in range(16)]
    eventi = []  # (inizio_s, durata_s, freq, voce)
    for b in range(battute):
        radice = progressione[b % len(progressione)]
        accordo = _accordo(radice)
        motivo = list(motivo_base)
        if b % 4 == 3:  # ogni quattro battute una variazione
            motivo = [caso.choice([0, 1, 2, None]) for _ in range(16)]
        for s, grado in enumerate(motivo):
            t0 = (b * 16 + s) * sedicesimo
            if grado is not None:
                semi = accordo[grado] + (12 if caso.random() < 0.25 else 0)
                if caso.random() < 0.15:  # nota di passaggio della scala
                    semi = caso.choice(SCALA)
                eventi.append((t0, sedicesimo * 0.9, _nota(semi, 5), "lead"))
        for q in range(4):  # basso: radice e quinta in ottavi
            t0 = (b * 16 + q * 4) * sedicesimo
            eventi.append((t0, sedicesimo * 1.8, _nota(radice, 2), "basso"))
            eventi.append((t0 + 2 * sedicesimo, sedicesimo * 1.8, _nota(radice + 7, 2), "basso"))
        for q in range(8):  # charleston sugli ottavi
            eventi.append(((b * 16 + q * 2) * sedicesimo, 0.03, 0.0, "hat"))

    n = int(secondi * FREQ)
    campioni = [0.0] * n
    rumore = random.Random(seme + 1)
    for inizio, durata, f, voce in eventi:
        i0 = int(inizio * FREQ)
        i1 = min(n, int((inizio + durata) * FREQ))
        for i in range(i0, i1):
            t = i / FREQ
            dentro = (i - i0) / FREQ
            inviluppo = max(0.0, 1 - dentro / durata) ** 0.6
            if voce == "lead":
                v = 0.18 * _quadra(f, t, 0.25) * inviluppo
            elif voce == "basso":
                v = 0.28 * _triangolo(f, t) * inviluppo
            else:
                v = 0.06 * (rumore.random() * 2 - 1) * inviluppo
            campioni[i] += v

    fade = int(1.5 * FREQ)
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FREQ)
        dati = bytearray()
        for i, v in enumerate(campioni):
            if i > n - fade:
                v *= (n - i) / fade
            dati += struct.pack("<h", int(max(-1.0, min(1.0, v)) * 30000))
        w.writeframes(bytes(dati))
    return out.getvalue()
