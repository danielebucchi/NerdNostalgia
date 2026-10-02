"""Unit: invio email fuori dalla richiesta."""
import time

from utils import mailer


def test_nothing_is_sent_when_email_is_disabled(monkeypatch):
    """Con le email spente non si apre nemmeno un thread: nei test eviterebbe
    che vada a cercare il database di produzione."""
    thread_creati = []
    monkeypatch.setattr(mailer, "_emails_enabled", lambda: False)
    monkeypatch.setattr(
        mailer, "_run_detached",
        lambda job, descr: thread_creati.append(descr),
    )

    mailer.order_notification(1)
    mailer.order_confirmation(1)
    mailer.shipping_notice(1)
    mailer.welcome(1)
    assert thread_creati == []


def test_failures_do_not_propagate(monkeypatch):
    """Un'email non partita non deve mai far fallire un ordine gia' pagato:
    l'errore resta nei log."""
    def esplode():
        raise RuntimeError("SMTP giu'")

    mailer._run_detached(esplode, "prova")
    time.sleep(0.2)   # il thread e' partito e ha gia' fallito in silenzio


def test_the_call_returns_before_the_job_finishes(monkeypatch):
    """E' il motivo di tutto: chi ha premuto il bottone non aspetta Gmail."""
    finito = []

    def lento():
        time.sleep(0.4)
        finito.append(True)

    mailer._run_detached(lento, "lento")
    # Se fosse sincrono, qui finito sarebbe gia' pieno
    assert finito == []
    time.sleep(0.7)
    assert finito == [True]
