"""
Freno agli invii di email.

Il rate limiting degli endpoint conta gli IP: contro una botnet non serve
a niente, perche' ogni richiesta arriva da un indirizzo diverso e nessun
contatore si riempie mai. Qui invece si conta quello che davvero fa
danno — quante email partono, e verso chi — e siccome il controllo sta
dentro send_email vale per ogni endpoint, compresi quelli che
aggiungeremo domani senza ricordarci di questo file.

Tre danni da evitare, in ordine di gravita':

1. Bruciare la quota SMTP. Gmail sta intorno alle 500 email al giorno:
   esaurirla vuol dire che le conferme d'ordine smettono di partire in
   silenzio, e l'attacco diventa un problema di vendite.
2. Usare il sito per tempestare di posta un estraneo. Chi riceve decine
   di messaggi "non richiesti" dal nostro dominio lo segnala come spam, e
   da li' in poi le email vere finiscono nella cartella sbagliata per
   tutti.
3. Riempire la casella dell'admin dal form dei contatti.

Le email legate a un ordine pagato passano sempre. Perdere una conferma
d'acquisto costa un cliente vero; per mandarne a raffica bisognerebbe
pagare altrettanti ordini, quindi quella strada si difende da sola.

I contatori vivono in memoria e ripartono a ogni riavvio: per fermare
una raffica, che dura minuti, e' piu' che sufficiente. NB: valgono per
processo — se un domani uvicorn girera' con piu' worker, i tetti vanno
divisi per il loro numero.
"""
import logging
import os
import threading
import time
from collections import deque

LOGGER = logging.getLogger("email_guard")

ORA = 3600
GIORNO = 24 * ORA

# Quante email puo' ricevere lo STESSO indirizzo. Un cliente vero ne vede
# una manciata nel giro di un acquisto; chi ne riceve dieci in un'ora non
# le ha chieste.
PER_DESTINATARIO_ORA = 5
PER_DESTINATARIO_GIORNO = 15

# Tetto complessivo, a protezione della quota SMTP. Tarato sotto il
# limite di Gmail (~500/giorno) per lasciare margine agli ordini veri,
# che passano comunque anche a tetto raggiunto.
TOTALE_ORA = 120
TOTALE_GIORNO = 350


class _Finestra:
    """Timestamp degli invii, con quelli vecchi buttati via a ogni lettura."""

    def __init__(self) -> None:
        self._t: deque[float] = deque()

    def quanti(self, adesso: float, durata: int) -> int:
        limite = adesso - durata
        while self._t and self._t[0] < limite:
            self._t.popleft()
        return len(self._t)

    def segna(self, adesso: float) -> None:
        self._t.append(adesso)


_lock = threading.Lock()
_per_destinatario: dict[str, _Finestra] = {}
_totale = _Finestra()


def _attivo() -> bool:
    """Interruttore d'emergenza: EMAIL_GUARD=0 lo spegne.

    Esiste per non restare bloccati da un tetto tarato male durante una
    giornata di vendite, non per tenerlo spento.
    """
    return os.getenv("EMAIL_GUARD", "1") != "0"


def consenti(destinatario: str, critica: bool = False) -> bool:
    """True se questa email puo' partire. Da chiamare una volta sola per
    invio: se dice di si', l'invio viene gia' conteggiato."""
    if not _attivo():
        return True

    adesso = time.time()
    chiave = (destinatario or "").strip().lower()

    with _lock:
        if not critica:
            # .get() e non _per_destinatario[chiave]: con un defaultdict la
            # sola lettura creerebbe la voce, e un attacco con indirizzi
            # inventati gonfierebbe la memoria anche mentre lo rifiutiamo.
            mio = _per_destinatario.get(chiave)
            if mio is None:
                mio = _Finestra()
            if mio.quanti(adesso, ORA) >= PER_DESTINATARIO_ORA:
                LOGGER.warning(
                    "Email non inviata: %s ha gia' ricevuto %s messaggi "
                    "nell'ultima ora", chiave, PER_DESTINATARIO_ORA,
                )
                return False
            if mio.quanti(adesso, GIORNO) >= PER_DESTINATARIO_GIORNO:
                LOGGER.warning(
                    "Email non inviata: %s ha gia' ricevuto %s messaggi "
                    "nelle ultime 24 ore", chiave, PER_DESTINATARIO_GIORNO,
                )
                return False

            if _totale.quanti(adesso, ORA) >= TOTALE_ORA:
                LOGGER.error(
                    "Tetto orario invii raggiunto (%s): email a %s non "
                    "inviata. Possibile attacco in corso.", TOTALE_ORA, chiave,
                )
                return False
            if _totale.quanti(adesso, GIORNO) >= TOTALE_GIORNO:
                LOGGER.error(
                    "Tetto giornaliero invii raggiunto (%s): email a %s non "
                    "inviata. Possibile attacco in corso.", TOTALE_GIORNO, chiave,
                )
                return False

        # Solo ora la voce si crea davvero: un invio rifiutato non lascia
        # traccia, cosi' la memoria resta legata agli invii riusciti e non
        # a quanti ne tenta un attacco.
        # Anche le critiche contano: servono a sapere quanta quota resta.
        _per_destinatario.setdefault(chiave, _Finestra()).segna(adesso)
        _totale.segna(adesso)

        # La memoria non deve crescere con gli indirizzi inventati da un
        # attacco: tolgo quelli che non hanno piu' niente in finestra.
        if len(_per_destinatario) > 5000:
            _ripulisci(adesso)

    return True


def _ripulisci(adesso: float) -> None:
    """Chiamata col lock gia' preso."""
    morti = [k for k, f in _per_destinatario.items() if f.quanti(adesso, GIORNO) == 0]
    for k in morti:
        del _per_destinatario[k]
    LOGGER.info("Pulite %s voci dal contatore invii", len(morti))


def azzera() -> None:
    """Solo per i test."""
    with _lock:
        _per_destinatario.clear()
        _totale._t.clear()
