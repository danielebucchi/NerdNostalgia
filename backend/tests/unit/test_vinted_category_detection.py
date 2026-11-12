"""Unit: riconoscimento categoria dal titolo degli annunci Vinted."""
import pytest

from utils.vinted_sync import _detect_category_slug


@pytest.mark.parametrize("title, slug", [
    ("Gormiti serie 1 lotto 10 personaggi", "gormiti"),
    ("Gormiti action figure Signore della Natura", "gormiti"),
    ("Bakugan Dragonoid con carte", "bakugan"),
    ("Beyblade Metal Fusion trottola", "beyblade"),
    ("Tamagotchi originale Bandai", "altri-giocattoli"),
    ("Lotto giocattoli anni 2000", "giocattoli"),
])
def test_toys_go_to_giocattoli(title, slug):
    assert _detect_category_slug(title) == slug


@pytest.mark.parametrize("title", [
    "Bakugan rise of resistance nintendo ds",
    "Gormiti Gli Eroi Della Natura Wii",
    "Beyblade Metal Fusion DS",
])
def test_toy_videogames_go_to_giochi(title):
    assert _detect_category_slug(title) == "giochi"


def test_console_only_in_description_keeps_toy():
    assert _detect_category_slug(
        "Gormiti lotto 5 personaggi", "vendo anche giochi per nintendo ds",
    ) == "gormiti"


def test_toy_merch_stays_gadget():
    assert _detect_category_slug("Portachiavi Gormiti") == "gadget"


def test_plain_action_figure_unchanged():
    assert _detect_category_slug("Action figure Goku NECA") == "action-figure"


@pytest.mark.parametrize("title", [
    "Ripristinavita psichico csoc-it041 crossroad of caos yu gi oh",
    "Alieno cucciolo crms-it084 cerimonia crisi yugioh",
    "Arcidemone drago rosso tiranno tdil-it050 the dark illusion yu-gi-oh",
])
def test_yugioh_spellings_go_to_yugioh(title):
    assert _detect_category_slug(title) == "yu-gi-oh"


def test_brand_alone_picks_the_category():
    # Titolo e descrizione dicono solo nome e set: il franchise e' nel brand.
    from utils.vinted_client import _parse_item
    item = _parse_item({
        "id": 10312549335,
        "title": "Dragonite v astro swsh236 swsh black star promos",
        "brand": "Pokémon",
    })
    assert item.brand == "Pokémon"
    assert _detect_category_slug(item.title, item.description, None, item.brand) == "pokemon"


@pytest.mark.parametrize("raw, brand", [
    ({"brand": "Yu-Gi-Oh!"}, "Yu-Gi-Oh!"),
    ({"brand_title": "OnePiece"}, "OnePiece"),
    ({"brand": {"title": "Spiderman"}}, "Spiderman"),
    ({"brand": "  "}, None),
    ({}, None),
])
def test_brand_title_shapes(raw, brand):
    from utils.vinted_client import _brand_title
    assert _brand_title(raw) == brand
