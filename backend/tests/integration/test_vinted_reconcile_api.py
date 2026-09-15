"""Test sul giro di riconciliazione Vinted: POST /api/vinted/import
(calcolo candidati) e POST /api/vinted/reconcile (archiviazione).

Il punto sensibile e' che un fetch parziale NON deve svuotare il catalogo:
la maggior parte di questi test verifica i guardrail, non l'happy path.
"""
import datetime as _dt
from datetime import datetime, timedelta

import pytest

from models.db import (
    Article,
    ArticleCondition,
    ArticleStatus,
    VintedStatus,
    VintedSyncLog,
)

# Un fetch sotto RECONCILE_MIN_SEEN non produce mai candidati: nei test che
# vogliono arrivare in fondo servono almeno 10 ID "visti".
FILLER_SEEN = list(range(900_000, 900_020))


def _article(admin_user, item_id, *, status=ArticleStatus.PUBLISHED,
             vinted_status=VintedStatus.LISTED, synced_at=None):
    return Article(
        user_id=admin_user.id,
        title=f"Game Boy #{item_id}",
        price=50,
        condition=ArticleCondition.USED,
        status=status,
        vinted_item_id=item_id,
        vinted_status=vinted_status,
        vinted_url=f"https://www.vinted.it/items/{item_id}",
        vinted_synced_at=synced_at or datetime(2026, 1, 1),
    )


@pytest.fixture()
def seed_catalog(db_session, admin_user):
    """3 articoli a catalogo: 2 PUBLISHED/LISTED, 1 gia' venduto."""
    rows = [
        _article(admin_user, 111),
        _article(admin_user, 222),
        _article(admin_user, 333, status=ArticleStatus.SOLD),
    ]
    for r in rows:
        db_session.add(r)
    db_session.commit()
    return rows


def _import(client, *, seen, items=None):
    return client.post(
        "/api/vinted/import",
        json={
            "items": items or [],
            "triggered_by": "remote",
            "seen_item_ids": seen,
        },
    )


# --------------------------- calcolo candidati ---------------------------
def test_candidati_sono_gli_articoli_non_visti(auth_client, seed_catalog):
    r = _import(auth_client, seen=[111] + FILLER_SEEN)
    assert r.status_code == 200
    body = r.json()
    assert body["reconcile_skipped_reason"] is None
    # 111 visto → resta; 222 non visto → candidato; 333 e' SOLD → ignorato
    assert body["reconcile_candidates"] == [222]


def test_articoli_sold_non_sono_candidati(auth_client, seed_catalog):
    r = _import(auth_client, seen=FILLER_SEEN)
    assert 333 not in r.json()["reconcile_candidates"]


def test_senza_seen_item_ids_nessuna_riconciliazione(auth_client, seed_catalog):
    """Chi non manda il campo (client vecchio) non deve innescare nulla."""
    r = auth_client.post(
        "/api/vinted/import", json={"items": [], "triggered_by": "remote"},
    )
    assert r.status_code == 200
    assert r.json()["reconcile_candidates"] == []
    assert r.json()["reconcile_skipped_reason"] is None


# --------------------------- guardrail ---------------------------
def test_fetch_minuscolo_non_produce_candidati(auth_client, seed_catalog):
    r = _import(auth_client, seen=[111, 222])
    body = r.json()
    assert body["reconcile_candidates"] == []
    assert "troppo piccolo" in body["reconcile_skipped_reason"]


def test_fetch_parziale_rispetto_alle_run_recenti_viene_bloccato(
    auth_client, db_session, seed_catalog,
):
    """Lo scenario da incubo: lo scroll del profilo si ferma a meta' e il
    catalogo viene giudicato sparito. La run precedente da 80 item fa da
    metro: 12 item sono il 15%, sotto la soglia del 70%."""
    db_session.add(VintedSyncLog(
        started_at=datetime(2026, 9, 1),
        finished_at=datetime(2026, 9, 1),
        triggered_by="remote",
        items_fetched=80,
    ))
    db_session.commit()

    r = _import(auth_client, seen=FILLER_SEEN[:12])
    body = r.json()
    assert body["reconcile_candidates"] == []
    assert "parziale" in body["reconcile_skipped_reason"]


def test_arretrato_di_orfani_non_blocca_la_riconciliazione(
    auth_client, db_session, admin_user,
):
    """Il metro sono le run recenti, non gli articoli a DB: 60 articoli
    orfani accumulati non devono impedire di smaltirli."""
    for item_id in range(500, 560):
        db_session.add(_article(admin_user, item_id))
    db_session.add(VintedSyncLog(
        started_at=datetime(2026, 9, 1),
        finished_at=datetime(2026, 9, 1),
        triggered_by="remote",
        items_fetched=20,
    ))
    db_session.commit()

    r = _import(auth_client, seen=FILLER_SEEN)
    body = r.json()
    assert body["reconcile_skipped_reason"] is None
    assert len(body["reconcile_candidates"]) == 60


# --------------------------- archiviazione ---------------------------
def test_reconcile_archivia_gli_item_confermati(
    auth_client, db_session, seed_catalog,
):
    db_session.add(VintedSyncLog(
        started_at=datetime(2026, 9, 10),
        finished_at=datetime(2026, 9, 10),
        triggered_by="remote",
        items_fetched=40,
    ))
    db_session.commit()

    r = auth_client.post("/api/vinted/reconcile", json={"missing_item_ids": [222]})
    assert r.status_code == 200
    assert r.json()["items_archived"] == 1

    db_session.expire_all()
    archiviato = db_session.query(Article).filter_by(vinted_item_id=222).one()
    vivo = db_session.query(Article).filter_by(vinted_item_id=111).one()
    assert archiviato.status == ArticleStatus.ARCHIVED
    assert archiviato.vinted_status == VintedStatus.NOT_LISTED
    assert vivo.status == ArticleStatus.PUBLISHED
    # archiviato, non cancellato: url e foto restano per lo storico
    assert archiviato.vinted_url is not None


def test_reconcile_rifiuta_articoli_toccati_dallultimo_import(
    auth_client, db_session, admin_user,
):
    """Secondo gate: anche se il client lo dichiara sparito, un articolo
    sincronizzato durante l'ultimo import e' vivo su Vinted."""
    inizio_import = datetime(2026, 9, 10, 3, 0)
    db_session.add(VintedSyncLog(
        started_at=inizio_import,
        finished_at=inizio_import + timedelta(minutes=5),
        triggered_by="remote",
        items_fetched=40,
    ))
    db_session.add(_article(
        admin_user, 777, synced_at=inizio_import + timedelta(minutes=2),
    ))
    db_session.commit()

    r = auth_client.post("/api/vinted/reconcile", json={"missing_item_ids": [777]})
    assert r.status_code == 200
    body = r.json()
    assert body["items_archived"] == 0
    assert body["items_skipped"] == 1

    db_session.expire_all()
    assert db_session.query(Article).filter_by(vinted_item_id=777).one().status == (
        ArticleStatus.PUBLISHED
    )


def test_reconcile_ignora_item_sconosciuti(auth_client, seed_catalog):
    r = auth_client.post("/api/vinted/reconcile", json={"missing_item_ids": [999999]})
    assert r.status_code == 200
    assert r.json()["items_archived"] == 0


def test_reconcile_richiede_admin(client, seed_catalog):
    r = client.post("/api/vinted/reconcile", json={"missing_item_ids": [222]})
    assert r.status_code in (401, 403)


def test_articolo_archiviato_sparisce_dal_catalogo_pubblico(
    auth_client, db_session, seed_catalog,
):
    """Il motivo per cui ARCHIVED e' sufficiente: la vetrina interroga
    /api/articles/?status=PUBLISHED."""
    auth_client.post("/api/vinted/reconcile", json={"missing_item_ids": [222]})

    r = auth_client.get("/api/articles/?status=PUBLISHED&limit=50")
    assert r.status_code == 200
    titoli = [a["title"] for a in r.json()["items"]]
    assert "Game Boy #111" in titoli
    assert "Game Boy #222" not in titoli
