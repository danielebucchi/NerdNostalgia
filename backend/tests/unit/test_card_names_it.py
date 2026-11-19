"""Unit: dove si trovano i nomi italiani, con le fonti finte."""
from utils import card_names_it as cn


def test_pokemon_card_and_set_from_tcgdex(monkeypatch):
    cn._cache_set.clear()
    risposte = {
        "https://api.tcgdex.net/v2/en/sets": [{"id": "sv08", "name": "Surging Sparks"}],
        "https://api.tcgdex.net/v2/it/sets/sv08": {"name": "Scintille Folgoranti",
                                                    "cards": [{"localId": "004", "name": "Durant-ex"}]},
    }
    monkeypatch.setattr(cn, "_get", lambda url, params=None: risposte.get(url))
    assert cn.cerca(5, "Surging Sparks", "004/191") == ("Durant-ex", "Scintille Folgoranti")
    # Numero senza zeri davanti (set vecchi o OCR): stessa carta
    assert cn.cerca(5, "Surging Sparks", "4/191")[0] == "Durant-ex"


def test_yugioh_italian_code_is_looked_up_as_english(monkeypatch):
    chiesti = []

    def finto(url, params=None):
        chiesti.append(params)
        if "cardsetsinfo" in url:
            return {"id": 46986421}
        return {"data": [{"name": "Mago Nero"}]}
    monkeypatch.setattr(cn, "_get", finto)
    assert cn.cerca(4, None, "LOB-IT005") == ("Mago Nero", None)
    assert chiesti[0] == {"setcode": "LOB-EN005"}


def test_a_source_down_leaves_the_english_names(monkeypatch):
    cn._cache_set.clear()
    monkeypatch.setattr(cn, "_get", lambda url, params=None: None)
    assert cn.cerca(5, "Surging Sparks", "004/191") == (None, None)
    assert cn.cerca(15, "Romance Dawn", "OP01-001") == (None, None)


def test_old_ex_sets_match_without_the_ex_prefix(monkeypatch):
    """CardTrader dice "EX Crystal Guardians", TCGdex "Crystal Guardians"."""
    cn._cache_set.clear()
    risposte = {
        "https://api.tcgdex.net/v2/en/sets": [{"id": "ex14", "name": "Crystal Guardians"}],
        "https://api.tcgdex.net/v2/it/sets/ex14": {"name": "EX Guardiani dei Cristalli", "cards": []},
    }
    monkeypatch.setattr(cn, "_get", lambda url, params=None: risposte.get(url))
    assert cn.cerca(5, "EX Crystal Guardians", "061/100") == (None, "EX Guardiani dei Cristalli")


def test_trainer_name_from_another_set_when_the_set_has_none(monkeypatch):
    """Set vecchio senza nomi italiani delle carte: Switch → Scambio da
    un'altra espansione (i kit introduttivi "tk-" per ultimi)."""
    cn._cache_set.clear()

    def finto(url, params=None):
        if url.endswith("/v2/en/sets"):
            return [{"id": "ex14", "name": "Crystal Guardians"}]
        if url.endswith("/v2/it/sets/ex14"):
            return {"name": "EX Guardiani dei Cristalli", "cards": []}
        if url.endswith("/v2/en/cards"):
            assert params == {"name": "eq:Switch"}
            return [{"id": "tk-xy-sy-4"}, {"id": "base1-95"}]
        if url.endswith("/v2/it/cards/base1-95"):
            return {"name": "Scambio"}
        return None
    monkeypatch.setattr(cn, "_get", finto)
    assert cn.cerca(5, "EX Crystal Guardians", "090/100", nome_inglese="Switch") == \
        ("Scambio", "EX Guardiani dei Cristalli")
