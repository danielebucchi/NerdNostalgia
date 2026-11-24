"""
Cosa dice il nome del file di uno scan.

Gli scan arrivano gia' nominati a mano, per esempio:

    93_PL.jpg        carta numero 93, condizione Played
    66_1ed_SP.jpg    numero 66, prima edizione, Slightly Played
    93_PL_002.jpg    seconda copia della 93 in Played

Il numero e' quello stampato sulla carta (in produzione coincide in 77
scan confermati su 78): serve quando l'OCR non lo legge. Condizione e
prima edizione sono decise da una persona con la carta in mano: valgono
piu' della stima dallo scan. Il contatore finale ("002") dice che e'
un'altra copia fisica, non un doppione: in collezione diventa quantita'.
"""
import re
from dataclasses import asdict, dataclass
from typing import Optional

# Le sigle usate sugli scan → condizioni di CardTrader.
SIGLE_CONDIZIONE = {
    "M": "Mint",
    "NM": "Near Mint",
    "SP": "Slightly Played",
    "MP": "Moderately Played",
    "PL": "Played",
    "PO": "Poor",
}

PRIMA_EDIZIONE = {"1ED", "1ST", "1A", "1AED"}


@dataclass
class DalNome:
    numero: Optional[str] = None          # "93"
    condizione: Optional[str] = None      # "Played"
    prima_edizione: bool = False
    copia: Optional[int] = None           # 2 per "_002"

    def vuoto(self) -> bool:
        return not (self.numero or self.condizione or self.prima_edizione or self.copia)

    def as_dict(self) -> dict:
        return asdict(self)


def leggi(nome_file: Optional[str]) -> DalNome:
    """Il nome senza estensione, a pezzi separati da _ - spazio o punto.
    Il primo pezzo numerico e' il numero della carta; un pezzo numerico
    successivo e' il contatore delle copie."""
    esito = DalNome()
    base = re.sub(r"\.[A-Za-z0-9]{2,5}$", "", (nome_file or "").strip())
    pezzi = [p for p in re.split(r"[_\-\s.]+", base) if p]
    for i, pezzo in enumerate(pezzi):
        alto = pezzo.upper()
        if pezzo.isdigit():
            if esito.numero is None and i == 0:
                esito.numero = str(int(pezzo))
            elif esito.numero is not None and esito.copia is None:
                esito.copia = int(pezzo)
        elif alto in SIGLE_CONDIZIONE and esito.condizione is None:
            esito.condizione = SIGLE_CONDIZIONE[alto]
        elif alto in PRIMA_EDIZIONE:
            esito.prima_edizione = True
    return esito
