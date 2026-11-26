"""Nostalgia: abbinamento severo con Wikipedia, anno da Wikidata."""
import pytest

from utils import nostalgia


@pytest.mark.parametrize("nostro, wiki, atteso", [
    ("Super mario galaxy nintendo wii", "Super Mario Galaxy", True),
    ("Final fantasy ix jpn ps1", "Final Fantasy IX", True),
    ("Batman Arkham Knight PS4 Videogioco PlayStation 4", "Batman: Arkham Knight", True),
    ("One piece unlimited cruise wii jpn", "One Piece: Unlimited Cruise SP", False),
    ("Prince of Persia i due troni e le sabbie del tempo", "Prince of Persia: I due troni", False),
    ("Star Wars Battlefront II PS4", "Star Wars: Battlefront II (videogioco 2017)", True),
    ("Jak 3 playstation 2", "Jak II", False),
])
def test_strict_title_match(nostro, wiki, atteso):
    assert nostalgia.stesso_titolo(nostro, wiki) is atteso


def test_year_and_summary_from_wikipedia(monkeypatch):
    nostalgia.card_names_it._cache_set.clear()

    def finto(url, params=None):
        if params and params.get("list") == "search":
            return {"query": {"search": [{"title": "Final Fantasy IX"}]}}
        if "summary" in url:
            return {"title": "Final Fantasy IX", "wikibase_item": "Q1", "extract": "Final Fantasy IX è un videogioco. Uscì nel 2000.",
                    "content_urls": {"desktop": {"page": "https://it.wikipedia.org/wiki/Final_Fantasy_IX"}}}
        return {"entities": {"Q1": {"claims": {
            "P31": [{"mainsnak": {"datavalue": {"value": {"id": "Q7889"}}}}],
            "P577": [{"mainsnak": {"datavalue": {"value": {"time": "+2000-07-07T00:00:00Z"}}}}]}}}}
    monkeypatch.setattr(nostalgia, "_get", finto)
    v = nostalgia.per_articolo("Final fantasy ix jpn ps1", "videogioco")
    assert (v.titolo, v.anno, v.data) == ("Final Fantasy IX", 2000, "2000-07-07")
    assert nostalgia.per_articolo("Final fantasy ix jpn ps1", "console") is None      # non e' una console
    assert nostalgia.frasi(v.riassunto, quante=1) == "Final Fantasy IX è un videogioco."
