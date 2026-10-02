"""Freno agli invii: quello che il rate limiting per IP non puo' fermare.

Una botnet ha un IP diverso per ogni richiesta, quindi i contatori degli
endpoint non si riempiono mai. Qui si conta quello che fa davvero danno:
quante email partono, e verso chi.
"""
import pytest

from utils import email_guard as G


@pytest.fixture(autouse=True)
def _pulito(monkeypatch):
    monkeypatch.delenv("EMAIL_GUARD", raising=False)
    G.azzera()
    yield
    G.azzera()


# --- protezione di chi riceve ---------------------------------------------


def test_a_normal_exchange_goes_through(client=None):
    """Un acquisto vero manda una manciata di messaggi: non devono
    inciampare nel freno."""
    for _ in range(G.PER_DESTINATARIO_ORA):
        assert G.consenti("cliente@test.it") is True


def test_the_same_address_cannot_be_flooded(client=None):
    for _ in range(G.PER_DESTINATARIO_ORA):
        G.consenti("vittima@test.it")

    assert G.consenti("vittima@test.it") is False


def test_blocking_one_address_does_not_block_the_others(client=None):
    """Altrimenti basterebbe tempestare un indirizzo qualsiasi per
    spegnere le email di tutto il sito."""
    for _ in range(G.PER_DESTINATARIO_ORA + 3):
        G.consenti("vittima@test.it")

    assert G.consenti("un-altro@test.it") is True


def test_the_address_is_counted_regardless_of_case(client=None):
    """Senza, basterebbe alternare le maiuscole per avere contatori nuovi."""
    for _ in range(G.PER_DESTINATARIO_ORA):
        G.consenti("Vittima@Test.IT")

    assert G.consenti("vittima@test.it") is False


# --- protezione della quota SMTP ------------------------------------------


def test_there_is_a_ceiling_on_the_total(client=None):
    """Esaurire la quota Gmail vuol dire che le conferme d'ordine smettono
    di partire in silenzio: l'attacco diventa un problema di vendite."""
    partite = 0
    for i in range(G.TOTALE_ORA + 50):
        # un indirizzo diverso ogni volta, come farebbe una botnet
        if G.consenti(f"vittima{i}@test.it"):
            partite += 1

    assert partite == G.TOTALE_ORA


# --- quello che deve passare comunque -------------------------------------


def test_order_email_goes_through_even_at_the_ceiling(client=None):
    """Perdere una conferma d'acquisto costa un cliente vero. Per abusarne
    bisognerebbe pagare un ordine a ogni email."""
    for i in range(G.TOTALE_ORA + 10):
        G.consenti(f"rumore{i}@test.it")

    assert G.consenti("compratore@test.it", critica=True) is True


def test_a_critical_email_ignores_the_per_recipient_limit(client=None):
    for _ in range(G.PER_DESTINATARIO_ORA + 5):
        G.consenti("compratore@test.it")

    assert G.consenti("compratore@test.it", critica=True) is True


def test_critical_emails_are_counted_anyway(client=None):
    """Contarle serve a sapere quanta quota resta davvero."""
    G.consenti("compratore@test.it", critica=True)

    # Dopo una critica, le normali verso lo stesso indirizzo sono una in meno
    normali = 0
    while G.consenti("compratore@test.it"):
        normali += 1

    assert normali == G.PER_DESTINATARIO_ORA - 1


# --- interruttore e memoria -----------------------------------------------


def test_it_can_be_switched_off(monkeypatch):
    """Serve a non restare bloccati da un tetto tarato male in una
    giornata di vendite."""
    monkeypatch.setenv("EMAIL_GUARD", "0")

    for _ in range(G.PER_DESTINATARIO_ORA + 10):
        assert G.consenti("chiunque@test.it") is True


def test_a_refused_send_leaves_no_trace(client=None):
    """Un attacco usa indirizzi inventati a ogni colpo: se ognuno
    lasciasse una voce, la memoria crescerebbe insieme all'attacco anche
    mentre lo stiamo rifiutando."""
    for i in range(6000):
        G.consenti(f"finto{i}@test.it")

    # Scatta per primo il tetto orario: da li' in poi non parte piu'
    # niente, quindi le voci tracciate si fermano e non seguono i 6000
    # tentativi.
    assert len(G._per_destinatario) == G.TOTALE_ORA
