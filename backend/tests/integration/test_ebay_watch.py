"""Integration: inserzioni eBay chiuse o nascoste da eBay → un'email, una volta."""
import pytest

from models.db import Article, ArticleCondition, ArticleStatus, PersonalCard


@pytest.fixture
def ebay_finto(monkeypatch):
    from utils import ebay_client as eb, ebay_watch, email as em
    stato = {"offerte": {}, "email": []}
    monkeypatch.setattr(eb, "is_configured", lambda: True)
    monkeypatch.setattr(eb, "get_offers", lambda sku: {"offers": stato["offerte"].get(sku, [])})
    monkeypatch.setattr(ebay_watch, "_motivo", lambda lid: "Questa inserzione viola le nostre regole")
    monkeypatch.setattr(em, "send_email", lambda **kw: stato["email"].append(kw) or True)
    return stato


def _offerta(status, venduti=0):
    return [{"listing": {"listingStatus": status, "soldQuantity": venduti}}]


def _in_vendita(db_session, admin_user):
    carta = PersonalCard(name="Crobat G", quantity=1, ebay_sku="NN-PC-1", ebay_offer_id="O1",
                         ebay_listing_id="800926565853")
    art = Article(user_id=admin_user.id, title="Venusaur 15 base set", price=50,
                  condition=ArticleCondition.USED, status=ArticleStatus.PUBLISHED,
                  ebay_sku="NN-ART-9", ebay_offer_id="OA9", ebay_listing_id="800952341542")
    db_session.add_all([carta, art])
    db_session.commit()
    return carta, art


def test_listing_ended_by_ebay_is_reported_once(db_session, admin_user, ebay_finto):
    from utils import ebay_watch
    _in_vendita(db_session, admin_user)
    ebay_finto["offerte"] = {"NN-PC-1": _offerta("ENDED"), "NN-ART-9": _offerta("ACTIVE")}

    esito = ebay_watch.run(db_session)
    assert [s["listing_id"] for s in esito["sparite"]] == ["800926565853"]
    testo = ebay_finto["email"][0]["text_body"]
    assert "Crobat G" in testo and "viola le nostre regole" in testo and "/itm/800926565853" in testo
    from utils.email import _config
    assert ebay_finto["email"][0]["to"] == _config()["to_admin"]

    # Il giro dopo non la segnala di nuovo
    assert ebay_watch.run(db_session)["sparite"] == [] and len(ebay_finto["email"]) == 1


def test_listing_sold_out_is_not_a_problem(db_session, admin_user, ebay_finto):
    from utils import ebay_watch
    _in_vendita(db_session, admin_user)
    ebay_finto["offerte"] = {"NN-PC-1": _offerta("ENDED", venduti=1), "NN-ART-9": _offerta("ACTIVE")}
    assert ebay_watch.run(db_session)["sparite"] == [] and ebay_finto["email"] == []


def test_back_active_then_gone_again_is_reported_again(db_session, admin_user, ebay_finto):
    from utils import ebay_watch
    _in_vendita(db_session, admin_user)
    ebay_finto["offerte"] = {"NN-PC-1": _offerta("ACTIVE"), "NN-ART-9": _offerta("ENDED")}
    ebay_watch.run(db_session)
    ebay_finto["offerte"]["NN-ART-9"] = _offerta("ACTIVE")
    ebay_watch.run(db_session)
    ebay_finto["offerte"]["NN-ART-9"] = _offerta("ENDED")
    ebay_watch.run(db_session)
    assert len(ebay_finto["email"]) == 2
