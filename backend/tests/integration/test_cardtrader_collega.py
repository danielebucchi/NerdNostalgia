"""Articoli messi a mano su CardTrader: collegati al prodotto, ritirati alla vendita."""
from datetime import datetime

import pytest

from models.db import Article, ArticleCondition, ArticleStatus, PersonalCard
from utils import cardtrader_client as ct
from utils import cardtrader_sync as cts


@pytest.fixture
def articolo(db_session, admin_user):
    def crea(blueprint, **extra):
        a = Article(user_id=admin_user.id, title=f"Carta {blueprint}", price=10, condition=ArticleCondition.USED,
                    status=ArticleStatus.PUBLISHED, quantity=1, images=["/static/x.webp"],
                    published_at=datetime.utcnow(), cardtrader_blueprint_id=blueprint, **extra)
        db_session.add(a)
        db_session.commit()
        return a
    return crea


def test_links_only_certain_matches(db_session, articolo):
    unico = articolo(1)
    doppio_a, doppio_b = articolo(2), articolo(2)       # due copie, un prodotto: quale?
    due_prodotti = articolo(3)                          # un articolo, due prodotti: quale?
    gia_preso = articolo(4)
    articolo(5, cardtrader_product_id=500)              # gia' collegato
    db_session.add(PersonalCard(name="X", cardtrader_blueprint_id=4, cardtrader_product_id=400))
    db_session.commit()
    prodotti = [{"id": 100, "blueprint_id": 1}, {"id": 200, "blueprint_id": 2},
                {"id": 300, "blueprint_id": 3}, {"id": 301, "blueprint_id": 3},
                {"id": 400, "blueprint_id": 4}, {"id": 500, "blueprint_id": 5}]

    assert cts.collega_prodotti(db_session, prodotti) == 1
    assert unico.cardtrader_product_id == 100
    assert not any(a.cardtrader_product_id for a in (doppio_a, doppio_b, due_prodotti, gia_preso))


def test_sale_unpublishes_unlinked_manual_listing(db_session, articolo, monkeypatch):
    a = articolo(111162, ebay_status=None)
    monkeypatch.setattr(ct, "is_configured", lambda: True)
    monkeypatch.setattr(ct, "my_products", lambda blueprint_id=None: [{"id": 472423435, "blueprint_id": 111162}])
    tolti = []
    monkeypatch.setattr(ct, "delete_product", lambda pid: tolti.append(pid))

    a.status = ArticleStatus.SOLD
    db_session.commit()
    cts.auto_unpublish_on_sold(db_session, a, "vinted")

    assert tolti == [472423435]
    assert a.cardtrader_product_id is None
