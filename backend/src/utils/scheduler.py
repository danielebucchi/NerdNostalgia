"""
APScheduler wrapper: pianifica un singolo job 'vinted_sync' che gira
ogni giorno all'ora configurata in vinted_settings.sync_hour.

Filosofia: il job ricarica le settings ad ogni run, cosi' una modifica
di sync_hour avra effetto al prossimo tick (entro 1h) senza riavvio.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
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


def start_scheduler() -> None:
    """Avvia lo scheduler in background. Disabilitabile con env DISABLE_SCHEDULER=1."""
    global _scheduler
    if os.getenv("DISABLE_SCHEDULER") == "1":
        LOGGER.info("Scheduler disabilitato da env DISABLE_SCHEDULER=1")
        return
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone=APP_TZ)
    # Job orario che decide internamente se eseguire (basato su sync_hour)
    _scheduler.add_job(
        _vinted_job,
        CronTrigger(minute=5),
        id="vinted_sync_hourly_check",
        replace_existing=True,
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
