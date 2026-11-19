"""Rivalutazione settimanale: segnala, non cambia i prezzi."""
from datetime import datetime, timedelta

from models.db import PersonalCard
from tests.integration.test_card_scanner_api import _carta_confermata, mondo_finto  # noqa: F401


def _vecchia_in_vendita(client, admin_headers, db_session, prezzo):
    carta = _carta_confermata(client, admin_headers)
    client.post(f"/api/card-scanner/cards/{carta['id']}/cardtrader", headers=admin_headers)
    card = db_session.get(PersonalCard, carta["id"])
    card.list_price = prezzo
    card.prices_updated_at = datetime.utcnow() - timedelta(days=10)
    db_session.commit()
    return card


def test_market_moved_is_reported_and_the_price_stays(client, admin_headers, db_session, monkeypatch):
    from utils import email as em, price_watch
    inviate = []
    monkeypatch.setattr(em, "send_email", lambda **kw: inviate.append(kw) or True)
    lontana = _vecchia_in_vendita(client, admin_headers, db_session, "2.00")   # il mercato dice ~5
    vicina = _vecchia_in_vendita(client, admin_headers, db_session, "5.00")

    esito = price_watch.run(db_session, pausa=0)
    assert esito["rivalutate"] == 2
    assert [s["card_id"] for s in esito["segnalate"]] == [lontana.id]
    db_session.refresh(lontana)
    assert float(lontana.list_price) == 2.00          # il prezzo non si tocca
    assert "in vendita a 2.00 €" in inviate[0]["text_body"]
    assert vicina.id not in [s["card_id"] for s in esito["segnalate"]]


def test_recently_valued_or_not_on_sale_are_skipped(client, admin_headers, db_session):
    from utils import price_watch
    fresca = _vecchia_in_vendita(client, admin_headers, db_session, "2.00")
    fresca.prices_updated_at = datetime.utcnow()
    ferma = _carta_confermata(client, admin_headers)          # mai messa in vendita
    db_session.commit()
    ids = [c.id for c in price_watch.da_rivalutare(db_session)]
    assert fresca.id not in ids and ferma["id"] not in ids
