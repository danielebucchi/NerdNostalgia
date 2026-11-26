"""
APScheduler wrapper: pianifica un singolo job 'vinted_sync' che gira
ogni giorno all'ora configurata in vinted_settings.sync_hour.

Filosofia: il job ricarica le settings ad ogni run, cosi' una modifica
di sync_hour avra effetto al prossimo tick (entro 1h) senza riavvio.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from models.db import VintedSettings
from utils.backup import run_backup
from utils.session import SessionLocal
from utils.vinted_sync import run_sync

LOGGER = logging.getLogger("scheduler")

APP_TZ_NAME = os.getenv("APP_TIMEZONE", "Europe/Rome")
APP_TZ = ZoneInfo(APP_TZ_NAME)

_scheduler: BackgroundScheduler | None = None


def _vinted_job():
    """Eseguito ogni ora: controlla se l'hour corrente coincide con sync_hour."""
    db = SessionLocal()
    try:
        settings = db.query(VintedSettings).order_by(VintedSettings.id.asc()).first()
        if settings is None or not settings.enabled:
            return
        now_local = datetime.now(tz=APP_TZ)
        if now_local.hour != settings.sync_hour:
            return
        if settings.last_run_at and settings.last_run_at.date() == now_local.date():
            return
        LOGGER.info("Cron Vinted sync triggered at hour %d (%s)", now_local.hour, APP_TZ_NAME)
        run_sync(db, triggered_by="cron")
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Cron Vinted job error: %s", exc)
    finally:
        db.close()


def _sales_job():
    """Vendite su CardTrader/eBay: la carta si ritira dagli altri canali."""
    from utils import sales_sync
    db = SessionLocal()
    try:
        esito = sales_sync.run(db)
        if esito["vendute"]:
            LOGGER.info("Vendite fuori dal sito: %s", esito["vendute"])
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Controllo vendite fallito: %s", exc)
    finally:
        db.close()


def _ebay_watch_job():
    """Inserzioni eBay chiuse o nascoste da eBay: email."""
    from utils import ebay_watch
    db = SessionLocal()
    try:
        esito = ebay_watch.run(db)
        if esito["sparite"]:
            LOGGER.info("Inserzioni eBay non piu' attive: %s", esito["sparite"])
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Controllo inserzioni eBay fallito: %s", exc)
    finally:
        db.close()


def _price_watch_job():
    """Rivalutazione settimanale: segnala i prezzi lontani dal mercato."""
    from utils import price_watch
    db = SessionLocal()
    try:
        price_watch.run(db)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Rivalutazione settimanale fallita: %s", exc)
    finally:
        db.close()


def _newsletter_job():
    """Venerdi' alle 18: nuovi arrivi ai clienti con consenso (se accesa)."""
    from utils import newsletter
    db = SessionLocal()
    try:
        esito = newsletter.run_settimanale(db)
        if esito:
            LOGGER.info("Newsletter: %s", esito)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Newsletter fallita: %s", exc)
    finally:
        db.close()


def _instagram_carousel_job(slot: str):
    """Ogni fascia oraria: il post del giorno e la rubrica, ciascuno solo se
    e' la sua fascia di oggi."""
    from utils import instagram, instagram_rubriche
    db = SessionLocal()
    try:
        instagram.post_del_giorno(db, slot)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Instagram, carosello fallito: %s", exc)
        db.rollback()
    try:
        instagram_rubriche.rubrica_del_giorno(db, slot)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Instagram, rubrica fallita: %s", exc)
    finally:
        db.close()


def _instagram_comments_job():
    from utils import instagram_rubriche
    db = SessionLocal()
    try:
        instagram_rubriche.rispondi_ai_commenti(db)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Instagram, risposte ai commenti non mandate: %s", exc)
    finally:
        db.close()


def _instagram_stats_job():
    from utils import instagram, instagram_stats
    db = SessionLocal()
    try:
        if instagram.acceso(db):
            instagram_stats.importa_storico(db)
            instagram_stats.aggiorna(db)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Instagram, statistiche non lette: %s", exc)
    finally:
        db.close()


def _instagram_report_job():
    from utils import instagram, instagram_stats
    db = SessionLocal()
    try:
        if instagram.acceso(db):
            instagram_stats.manda_report(db)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Instagram, report fallito: %s", exc)
    finally:
        db.close()


def _instagram_reel_job():
    from utils import instagram_reel
    db = SessionLocal()
    try:
        instagram_reel.pubblica(db)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Instagram, Reel del mese fallito: %s", exc)
    finally:
        db.close()


def _instagram_stories_job():
    from utils import instagram
    db = SessionLocal()
    try:
        instagram.pubblica_storie(db)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Instagram, Storie fallite: %s", exc)
    finally:
        db.close()


def _instagram_token_job():
    from utils import instagram
    db = SessionLocal()
    try:
        instagram.rinnova_token(db)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Instagram, rinnovo token fallito: %s", exc)
    finally:
        db.close()


def _telegram_ripesca_job():
    from utils import telegram_channel
    db = SessionLocal()
    try:
        telegram_channel.ripesca(db)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Telegram, ripescaggio fallito: %s", exc)
    finally:
        db.close()


def _price_guide_job():
    from utils import price_guide
    db = SessionLocal()
    try:
        price_guide.aggiorna(db)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Guida prezzi non aggiornata: %s", exc)
    finally:
        db.close()


def _price_guide_da_rifare() -> bool:
    from utils import price_guide
    db = SessionLocal()
    try:
        return price_guide.da_rifare(db)
    except Exception:  # noqa: BLE001 — tabella non ancora creata
        return False
    finally:
        db.close()


def _italian_names_job():
    """Nomi italiani alle carte che non li hanno (e titoli del sito)."""
    from utils.card_listing import aggiorna_nomi_italiani
    db = SessionLocal()
    try:
        aggiorna_nomi_italiani(db)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Nomi italiani: %s", exc)
    finally:
        db.close()


def start_scheduler() -> None:
    """Avvia lo scheduler in background.

    DISABLE_SCHEDULER=1 spegne tutto (test, sviluppo).
    DISABLE_VINTED_SYNC=1 spegne solo la sync Vinted: in produzione Vinted
    blocca l'IP del server (Cloudflare) e la sync gira dal Mac. Prima per
    questo si usava DISABLE_SCHEDULER, che pero' spegneva anche backup,
    controllo vendite e rivalutazione: da luglio non si facevano backup."""
    global _scheduler
    if os.getenv("DISABLE_SCHEDULER") == "1":
        LOGGER.info("Scheduler disabilitato da env DISABLE_SCHEDULER=1")
        return
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone=APP_TZ)
    if os.getenv("DISABLE_VINTED_SYNC") == "1":
        LOGGER.info("Sync Vinted dal server spenta (DISABLE_VINTED_SYNC=1): gira dal Mac")
    else:
        # Job orario che decide internamente se eseguire (basato su sync_hour)
        _scheduler.add_job(
            _vinted_job,
            CronTrigger(minute=5),
            id="vinted_sync_hourly_check",
            replace_existing=True,
        )
    # Vendite su CardTrader/eBay ogni 15 minuti: una carta venduta li' non
    # deve restare in vendita sul sito e sull'altro marketplace.
    _scheduler.add_job(
        _sales_job,
        CronTrigger(minute="*/15"),
        id="marketplace_sales_sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # Ogni ora: inserzioni eBay che eBay ha chiuso o nascosto (es. per una
    # regola) mentre la carta o l'articolo risultano in vendita.
    _scheduler.add_job(
        _ebay_watch_job,
        CronTrigger(minute=40),
        id="ebay_listings_watch",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # Lunedi' alle 04:15: rivaluta le carte in vendita e segnala per email
    # quelle il cui prezzo di mercato si e' spostato (i prezzi non li tocca).
    _scheduler.add_job(
        _price_watch_job,
        CronTrigger(day_of_week="mon", hour=4, minute=15),
        id="weekly_price_watch",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # Nomi italiani: poco dopo l'avvio (cosi' un deploy sistema le carte che
    # ne erano senza) e poi ogni notte alle 04:45 per le nuove.
    _scheduler.add_job(
        _italian_names_job,
        CronTrigger(hour=4, minute=45),
        id="italian_names",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(tz=APP_TZ) + timedelta(minutes=2),
    )
    # Newsletter dei nuovi arrivi: venerdi' 18:00, parte solo se accesa in
    # Impostazioni (newsletter_enabled).
    _scheduler.add_job(
        _newsletter_job,
        CronTrigger(day_of_week="fri", hour=18, minute=0),
        id="weekly_newsletter",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # Instagram (parte solo se acceso in Impostazioni): il post del giorno
    # in una delle fasce orarie, quella che le statistiche dicono raggiunga
    # piu' persone (instagram_stats.slot_di_oggi); le Storie dei pezzi sopra
    # soglia ogni mezz'ora di giorno; le statistiche ogni due ore (quelle
    # delle Storie Instagram le tiene solo 24 ore); il report il lunedi'
    # mattina; il Reel dei venduti il primo del mese; il rinnovo del token
    # il lunedi' alle 05:00.
    from utils.instagram_stats import SLOT
    for slot in SLOT:
        ora, minuto = slot.split(":")
        _scheduler.add_job(
            _instagram_carousel_job,
            CronTrigger(hour=int(ora), minute=int(minuto)),
            args=[slot],
            id=f"instagram_post_{ora}{minuto}",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
    _scheduler.add_job(
        _instagram_comments_job,
        CronTrigger(minute="*/10"),
        id="instagram_comments",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.add_job(
        _instagram_stats_job,
        CronTrigger(hour="*/2", minute=50),
        id="instagram_stats",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.add_job(
        _instagram_report_job,
        CronTrigger(day_of_week="mon", hour=9, minute=0),
        id="instagram_report",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.add_job(
        _instagram_reel_job,
        CronTrigger(day=1, hour=18, minute=0),
        id="instagram_reel",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.add_job(
        _instagram_stories_job,
        CronTrigger(hour="9-21", minute="10,40"),
        id="instagram_stories",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.add_job(
        _instagram_token_job,
        CronTrigger(day_of_week="mon", hour=5, minute=0),
        id="instagram_token",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # Telegram: nei giorni senza nuovi arrivi, alle 13 e alle 20 un articolo
    # dal catalogo in "Nuovi Arrivi" (telegram_channel.ripesca).
    _scheduler.add_job(
        _telegram_ripesca_job,
        CronTrigger(hour="13,20", minute=0),
        id="telegram_ripesca",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # Guida prezzi delle carte Pokémon (pagine pubbliche "quanto vale"):
    # domenica alle 02:00, e pochi minuti dopo l'avvio se e' vuota o fatta
    # da una versione precedente del codice.
    # (next_run_time=None metterebbe il job in pausa: si passa solo se serve.)
    subito = {"next_run_time": datetime.now(tz=APP_TZ) + timedelta(minutes=5)} if _price_guide_da_rifare() else {}
    _scheduler.add_job(
        _price_guide_job,
        CronTrigger(day_of_week="sun", hour=2, minute=0),
        id="price_guide",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        **subito,
    )
    # Backup giornaliero (SQLite snapshot + tar uploads) alle 03:30 locali
    _scheduler.add_job(
        run_backup,
        CronTrigger(hour=3, minute=30),
        id="daily_backup",
        replace_existing=True,
    )
    _scheduler.start()
    LOGGER.info("Scheduler avviato (tz=%s)", APP_TZ_NAME)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
