"""Unit: la prima pagina del guardaroba Vinted, che arriva nell'HTML e non
via XHR, va riletta a mano e messa in testa."""
from urllib.parse import parse_qs, urlsplit

from utils.vinted_client import _first_page_url, _prepend_items, _replay_headers


def test_first_page_url_keeps_per_page():
    # "per_page=20" contiene "page=2": un replace di stringa lo rompeva.
    url = _first_page_url(
        "https://www.vinted.it/api/v2/wardrobe/3175004751/items?page=2&per_page=20"
    )
    query = parse_qs(urlsplit(url).query)
    assert query == {"page": ["1"], "per_page": ["20"]}
    assert urlsplit(url).path == "/api/v2/wardrobe/3175004751/items"


def test_replay_headers_keeps_tokens_drops_browser_ones():
    headers = _replay_headers({
        "accept": "application/json",
        "x-csrf-token": "t",
        "x-anon-id": "a",
        "cookie": "c",
        "referer": "r",
        "user-agent": "ua",
        "sec-ch-ua": "x",
        "priority": "u=1",
    })
    assert headers == {"accept": "application/json", "x-csrf-token": "t", "x-anon-id": "a"}


def test_prepend_items_puts_newest_first_without_duplicates():
    collected = [{"id": 3}, {"id": 4}]
    seen = {3, 4}
    added = _prepend_items(collected, seen, [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 1}])
    assert [r["id"] for r in collected] == [1, 2, 3, 4]
    assert added == 2
    assert seen == {1, 2, 3, 4}


def test_prepend_items_skips_malformed():
    collected = [{"id": 5}]
    seen = {5}
    added = _prepend_items(collected, seen, [{"title": "senza id"}, {"id": "x"}])
    assert collected == [{"id": 5}]
    assert added == 0
