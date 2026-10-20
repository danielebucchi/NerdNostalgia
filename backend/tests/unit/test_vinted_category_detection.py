"""Unit: riconoscimento categoria dal titolo degli annunci Vinted."""
import pytest

from utils.vinted_sync import _detect_category_slug, _matches_nn_keywords


@pytest.mark.parametrize("title, slug", [
    ("Gormiti serie 1 lotto 10 personaggi", "gormiti"),
    ("Gormiti action figure Signore della Natura", "gormiti"),
    ("Bakugan Dragonoid con carte", "bakugan"),
    ("Beyblade Metal Fusion trottola", "beyblade"),
    ("Tamagotchi originale Bandai", "altri-giocattoli"),
    ("Lotto giocattoli anni 2000", "giocattoli"),
])
def test_toys_go_to_giocattoli(title, slug):
    assert _matches_nn_keywords(title)
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
