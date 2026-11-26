"""Unit: quali job partono. In produzione DISABLE_SCHEDULER=1 (messo per
spegnere la sync Vinted) spegneva anche backup e controllo vendite: da
luglio niente backup. Ora la sync Vinted ha il suo interruttore."""
from utils import scheduler


def _avvia(monkeypatch, **env):
    for k in ("DISABLE_SCHEDULER", "DISABLE_VINTED_SYNC"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(scheduler, "_scheduler", None)
    scheduler.start_scheduler()
    try:
        return {j.id for j in scheduler._scheduler.get_jobs()} if scheduler._scheduler else set()
    finally:
        scheduler.stop_scheduler()


def test_without_vinted_the_other_jobs_still_run(monkeypatch):
    jobs = _avvia(monkeypatch, DISABLE_VINTED_SYNC="1")
    assert jobs == {"daily_backup", "marketplace_sales_sync", "weekly_price_watch", "italian_names",
                    "ebay_listings_watch", "weekly_newsletter",
                    "instagram_post_1230", "instagram_post_1830", "instagram_post_2100",
                    "instagram_stories", "instagram_stats", "instagram_report", "instagram_reel",
                    "instagram_token"}


def test_everything_by_default(monkeypatch):
    assert "vinted_sync_hourly_check" in _avvia(monkeypatch)


def test_disable_scheduler_still_turns_everything_off(monkeypatch):
    assert _avvia(monkeypatch, DISABLE_SCHEDULER="1") == set()
