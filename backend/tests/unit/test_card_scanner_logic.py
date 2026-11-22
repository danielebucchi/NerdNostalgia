"""Unit: lettura dei codici stampati, abbinamento, prezzi.

Niente Tesseract e niente CardTrader: si parte dal testo che l'OCR
restituirebbe e da un indice finto.
"""
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

from models.db import CardBlueprint
from utils import card_index as ci
from utils import card_pricing as cp
from utils.card_ocr import LetturaCarta, crop_to_card, parse_codes, upright


# --- codici stampati ------------------------------------------------------


def test_pokemon_number_and_set_code():
    l = parse_codes({"bottom": "Illus. 5ban Graphics\nSSP EN 004/191 ★"}, "pokemon")
    assert (l.number, l.total, l.printed_code) == ("004", "191", "004/191")
    assert l.set_codes == ["SSP"]
    assert l.language == "en"


def test_ocr_letter_o_inside_digits_is_a_zero():
    l = parse_codes({"bottom": "0O4/1O2"}, "pokemon")
    assert (l.number, l.total) == ("004", "102")


def test_magic_keeps_every_plausible_set_code():
    """La D di DMU letta O: si tengono tutte, decide l'elenco delle
    espansioni vere."""
    l = parse_codes({"bottom": "133/281 R\nOMU+EN Magali Villeneuve"}, "magic")
    assert l.number == "133"
    assert "OMU" in l.set_codes
    assert l.language == "en"


def test_yugioh_code_gives_set_number_and_language():
    l = parse_codes({"full": "SKULL SERVANT\n LOB-IT004 \nATK/ 300"}, "yugioh")
    assert (l.set_code, l.number, l.language) == ("LOB", "004", "it")
    assert l.printed_code == "LOB-IT004"


def test_one_piece_code():
    l = parse_codes({"bottom": "Alvida Buggy Pirates OP01-064 ©"}, "onepiece")
    assert (l.number, l.set_code) == ("OP01-064", "OP01")


def test_nothing_read_is_said():
    l = parse_codes({"bottom": "illustrazione"}, "pokemon")
    assert l.number is None
    assert "numero non letto" in l.notes


def test_scanner_bed_is_cropped_and_card_turned_upright():
    scan = Image.new("RGB", (900, 700), (250, 250, 250))
    ImageDraw.Draw(scan).rectangle((100, 80, 700, 520), fill=(30, 60, 160))
    card = upright(crop_to_card(scan))
    assert card.height > card.width
    assert abs(card.height - 601) <= 4 and abs(card.width - 441) <= 4


# --- abbinamento ----------------------------------------------------------


def _bp(id_, name, number, exp_id, exp_code, exp_name, dhash=None):
    return CardBlueprint(
        id=id_, game_id=5, expansion_id=exp_id, expansion_code=exp_code,
        expansion_name=exp_name, name=name, collector_number=number,
        number_norm=ci._norm_number(number), image_url=None, dhash=dhash,
    )


@pytest.fixture()
def indice(db_session, monkeypatch):
    from utils import cardtrader_client as ct
    monkeypatch.setattr(ct, "expansions_cached", lambda ttl=3600: [
        {"id": 1, "game_id": 5, "code": "ssp", "name": "Surging Sparks"},
        {"id": 2, "game_id": 5, "code": "svi", "name": "Scarlet & Violet"},
        {"id": 3, "game_id": 5, "code": "bs", "name": "Base Set"},
    ])
    uguale = "f" * 64
    db_session.add_all([
        _bp(10, "Durant ex", "004", 1, "ssp", "Surging Sparks", dhash=uguale),
        _bp(11, "Scatterbug", "005", 1, "ssp", "Surging Sparks", dhash="0" * 64),
        _bp(20, "Cacnea", "005", 2, "svi", "Scarlet & Violet", dhash="0" * 64),
        _bp(21, "Durant", "004", 2, "svi", "Scarlet & Violet", dhash="0f" * 32),
        _bp(30, "Charizard", "004", 3, "bs", "Base Set", dhash="0" * 64),
        _bp(31, "Charizard", "191", 1, "ssp", "Surging Sparks"),
    ])
    db_session.commit()
    return uguale


def test_set_code_and_number_pick_the_card(db_session, indice):
    l = LetturaCarta(number="004", total="191", set_codes=["SSP"], name_text="Durant ex")
    res = ci.match(db_session, 5, l, indice)
    assert res["candidates"][0]["blueprint_id"] == 10
    assert res["confidence"] == "alta"


def test_misread_number_is_rescued_by_name_and_image(db_session, indice):
    """OCR legge 005 invece di 004: la carta giusta resta prima."""
    l = LetturaCarta(number="005", total="191", name_text="Ge Durant x fw 90")
    res = ci.match(db_session, 5, l, indice)
    assert res["candidates"][0]["blueprint_id"] == 10
    assert res["confidence"] != "alta"


def test_misread_set_code_is_corrected(db_session, indice):
    assert [e["code"] for e in ci.resolve_set_codes(5, ["WH", "55P"])] == ["ssp"]


def test_fixed_expansion_limits_the_candidates(db_session, indice):
    l = LetturaCarta(number="004")
    res = ci.match(db_session, 5, l, None, expansion_id=3)
    assert [c["blueprint_id"] for c in res["candidates"]] == [30]


def test_variant_suffix_counts_as_same_number():
    assert ci._numero_compatibile("op01064b", "op01064") == 1
    assert ci._numero_compatibile("250", "25") == 0


def test_dhash_tells_same_from_different():
    a = Image.new("RGB", (60, 84), "white")
    ImageDraw.Draw(a).ellipse((10, 10, 50, 50), fill="red")
    b = Image.new("RGB", (60, 84), "white")
    ImageDraw.Draw(b).rectangle((5, 40, 55, 80), fill="blue")
    assert ci.similarity(ci.dhash(a), ci.dhash(a.resize((300, 420)))) > 0.9
    assert ci.similarity(ci.dhash(a), ci.dhash(b)) < 0.8


# --- prezzi ---------------------------------------------------------------


def _vendita(price, title="Durant ex 004/191", date="2026-11-01"):
    return {"title": title, "price": price, "date": date, "url": None}


def test_last_ten_sales_averaged_without_graded_and_lots():
    vendite = [_vendita(2.0, date=f"2026-10-{d:02d}") for d in range(1, 13)]
    vendite += [
        _vendita(150.0, "Durant ex 004/191 PSA 10", "2026-11-10"),
        _vendita(20.0, "Lotto 10 carte Surging Sparks", "2026-11-11"),
        _vendita(4.0, date="2026-11-12"),
    ]
    r = cp.summarize_sold(vendite)
    assert r["count"] == 10
    assert r["sales"][0]["price"] == 4.0          # la piu' recente
    assert r["avg"] == pytest.approx((4.0 + 9 * 2.0) / 10)


def test_ex_in_card_name_is_not_excluded():
    assert cp.summarize_sold([_vendita(3.0, "Charizard ex 223/197 IT")])["count"] == 1


def test_suggested_is_between_the_two():
    # Minimo CardTrader + ricarico; eBay solo senza offerte CardTrader
    assert cp.suggested(4.0, 6.0) == 4.40
    assert cp.suggested(None, 6.0) == 6.0
    assert cp.suggested(None, None) is None


def test_markup_shrinks_as_the_price_grows():
    assert cp.ricarico(2.60) == 2.90       # Scambio: non 7,14
    assert cp.ricarico(0.50) == 0.60       # sotto 1 €: +0,10
    assert cp.ricarico(10.00) == 10.70     # +7%
    assert cp.ricarico(30.00) == 31.50     # +5%
    assert cp.ricarico(100.00) == 103.00   # +3%


def test_manual_prices_accept_italian_decimals():
    assert cp.parse_manual_prices("12,50 € 9.90; 15\n11") == [12.5, 9.9, 15.0, 11.0]


def test_ebay_query_uses_printed_code():
    card = SimpleNamespace(name="Durant ex", printed_code="004/191",
                           card_number="004", collection="Surging Sparks")
    assert cp.ebay_query(card) == "Durant ex 004/191"
    assert "LH_Sold=1" in cp.ebay_sold_url(card)


# --- versioni, reverse, prima edizione, condizione --------------------------

from utils import card_features as cf  # noqa: E402


def _cand(bid, name, number, sim, version=None, exp=1):
    return {"blueprint_id": bid, "name": name, "number": number, "version": version,
            "expansion_id": exp, "image_similarity": sim, "score": 30, "number_match": True}


def test_close_alternate_art_is_flagged():
    c = [_cand(1, "Alvida", "OP01-064", 0.83), _cand(2, "Alvida", "OP01-064b", 0.81, "Alternate Art")]
    assert "OP01-064b Alternate Art" in ci._nota_varianti(c)


def test_alternate_art_clearly_different_is_not_flagged():
    c = [_cand(1, "Alvida", "OP01-064", 0.83), _cand(2, "Alvida", "OP01-064b", 0.5, "Alternate Art")]
    assert ci._nota_varianti(c) is None


def test_reprint_with_the_same_art_in_another_set_is_flagged():
    """OP08-076 esiste anche nelle promo e nel Premium Booster, stessa arte."""
    c = [_cand(1, "It's to Die For...", "OP08-076", 0.75),
         _cand(2, "It's to Die For...", "OP08-076", 0.75, exp=2)]
    c[1]["expansion_name"] = "PRB-02"
    assert "OP08-076 in PRB-02" in ci._nota_varianti(c)


def test_reprint_that_looks_different_is_not_flagged():
    c = [_cand(1, "Charizard", "004", 0.99), _cand(2, "Charizard", "004", 0.88, exp=2)]
    assert ci._nota_varianti(c) is None


def test_one_piece_code_read_with_letters_for_digits():
    """Bianco su viola: Tesseract legge "OPOS-O76" per OP08-076."""
    l = parse_codes({"bottom": "HE RAR ED\n\nopos-o76ta @"}, "onepiece")
    assert l.set_codes == ["OP05", "OP08"]
    assert {l.number, *l.alt_numbers} == {"OP05-076", "OP08-076"}


def test_yugioh_first_edition_is_read():
    assert cf.first_edition(None, None, "yugioh", "LOB-EN001 1st Edition")["value"] is True
    assert cf.first_edition(None, None, "yugioh", "SDK-I001 1a Edizione")["value"] is True
    assert cf.first_edition(None, None, "yugioh", "LOB-EN001")["value"] is False


def _carta_finta():
    """Bordo giallo, riquadro dell'illustrazione, testo piatto."""
    img = Image.new("RGB", (630, 880), (240, 200, 30))
    d = ImageDraw.Draw(img)
    d.rectangle((30, 30, 600, 850), fill=(200, 210, 220))
    d.rectangle((63, 97, 567, 440), fill=(60, 120, 60))
    for i in range(0, 500, 12):
        d.line((63 + i, 97, 63 + i, 440), fill=(30, 80 + i % 100, 30), width=4)
    return img


def test_pokemon_first_edition_stamp_compared_with_the_official_image():
    ref = _carta_finta()
    timbrata = ref.copy()
    ImageDraw.Draw(timbrata).ellipse((45, 445, 90, 490), fill=(10, 10, 10))
    assert cf.first_edition(timbrata, ref, "pokemon", "")["value"] is True
    assert cf.first_edition(ref.copy(), ref, "pokemon", "")["value"] is False


def test_reverse_grain_outside_the_artwork():
    import random
    random.seed(3)
    ref = _carta_finta()
    rev = ref.copy()
    d = ImageDraw.Draw(rev)
    for _ in range(3000):
        x, y = random.randint(50, 580), random.randint(510, 760)
        d.rectangle((x, y, x + 4, y + 4), fill=random.choice([(255, 255, 255), (90, 90, 90)]))
    assert cf.foil(rev, ref, "pokemon")["value"] is True
    assert cf.foil(ref.copy(), ref, "pokemon")["value"] is False


def test_whitened_edges_lower_the_condition():
    import random
    random.seed(4)
    pulita = _carta_finta()
    assert cf.condition(pulita)["value"] == "Near Mint"
    usurata = pulita.copy()
    d = ImageDraw.Draw(usurata)
    for _ in range(900):
        x, y = random.choice([(random.randint(0, 12), random.randint(0, 879)),
                              (random.randint(0, 629), random.randint(0, 12))])
        d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(250, 250, 250))
    assert cf.condition(usurata)["value"] in ("Moderately Played", "Played", "Poor")


def test_never_mint_and_white_border_is_not_measured():
    bianca = Image.new("RGB", (630, 880), (250, 250, 250))
    r = cf.condition(bianca)
    assert r["value"] is None and "bianco" in r["reason"]


def test_language_from_card_text_beats_noise_next_to_the_set_code():
    testo = ("Una sola volta durante il tuo turno, quando metti Crobat dalla tua mano "
             "nella tua Panchina, puoi mettere 1 segnalino danno su 1 dei Pokémon del tuo avversario. "
             "Il Pokémon Difensore è Avvelenato.")
    l = parse_codes({"bottom": "GE · ES", "full": testo}, "pokemon")
    assert l.language == "it"


def test_base_set_italian_with_little_text_is_not_read_as_noise_language():
    """Testo OCR vero di due carte Base Set italiane finite in tedesco e
    spagnolo: poco testo, e rumore scambiato per sigla + lingua."""
    diglett = ("Pokémon Base\n\nlett\n\n30 pv @\n\ntaipo. Lunghezza: 0,2 m; Peso: 0,8 kg.\n\nFossa\n\n"
               "Fangosberla\n\ndebolezza resistenza costo di ritirata\n\n4) -30\n\nAS\n\n"
               "dove sopravvive mangiando\n\nSeed Oe\n\ntanto risale in superficie. LIVE")
    l = parse_codes({"bottom": "IR DE", "full": diglett}, "pokemon")
    assert l.language == "it"

    super_pozione = ("OZIO!\n\nScarta una carta Energia\n\nassegnata a uno dei tuoi\n\n"
                     "Pokémon per poter togliere al\n\nquel Pokémon\n\nmassimo 4 segnalini danno da\n\n"
                     "es ES eae ee")
    l = parse_codes({"bottom": "DA ES", "full": super_pozione}, "pokemon")
    assert l.language == "it"


def test_set_code_language_still_counts_when_the_text_says_nothing():
    l = parse_codes({"bottom": "Illus. 5ban Graphics\nSSP EN 004/191", "full": "Pikachu ex 200"}, "pokemon")
    assert l.language == "en"


def test_set_only_in_japanese_has_no_language_choice():
    assert ci.lingue("pokemon_language:en|it|fr,pokemon_reverse") == {"en", "it", "fr"}
    assert ci.lingue("first_edition") == set()
    assert ci.lingue(None) is None


# --- apprendimento dalle conferme -------------------------------------------

from models.db import OcrCorrection  # noqa: E402
from utils import card_learning as learn  # noqa: E402


def test_ocr_confusions_are_learned_from_corrections(db_session):
    db_session.add_all([
        OcrCorrection(game_id=15, kind="number", read_text="O7E", true_text="076"),
        OcrCorrection(game_id=15, kind="set", read_text="OPOS", true_text="OP08"),
        OcrCorrection(game_id=15, kind="set", read_text="OPOS", true_text="OP08"),
        OcrCorrection(game_id=15, kind="set", read_text="OP0S", true_text="OP05"),
    ])
    db_session.commit()
    appreso = learn.confusions(db_session, 15)
    assert appreso["S"] == "85"        # piu' spesso 8 che 5
    assert appreso["E"] == "6"         # confusione che le regole fisse non hanno


def test_learned_confusion_reads_a_code_the_rules_could_not():
    """"OP08-O7E": la E per 6 l'ha insegnata una correzione."""
    senza = parse_codes({"bottom": "OP08-O7E"}, "onepiece")
    con = parse_codes({"bottom": "OP08-O7E"}, "onepiece", {"E": "6"})
    assert senza.number is None
    assert con.number == "OP08-076"
    assert (con.raw_set, con.raw_number) == ("OP08", "O7E")


def test_learned_order_puts_the_usual_mistake_first():
    l = parse_codes({"bottom": "OPOS-076"}, "onepiece", {"S": "85"})
    assert l.set_codes == ["OP08", "OP05"]


def test_leading_zeros_are_not_a_reading_mistake():
    assert learn._coppie("47", "047") == []
    assert learn._coppie("0O4", "004") == [("O", "0")]


def test_thresholds_need_enough_examples_on_both_sides():
    pochi = [(1.9, True)] * 3 + [(0.9, False)] * 10
    assert learn.soglie_binarie(pochi) is None
    esempi = [(s, True) for s in (1.4, 1.5, 1.6, 1.7, 1.8, 2.0)] + \
             [(s, False) for s in (0.8, 0.9, 1.0, 1.0, 1.1, 1.2)]
    t = learn.soglie_binarie(esempi)
    assert 1.1 <= t["no"] < t["si"] <= 1.5


def test_wear_limits_learned_from_confirmed_conditions():
    esempi = [(0.002, "Near Mint")] * 6 + [(0.03, "Slightly Played")] * 6
    limiti = learn.soglie_usura(esempi)
    assert limiti[0][1] == "Near Mint" and 0.002 < limiti[0][0] < 0.03
    assert limiti[1][0] is None  # SP/MP: nessun esempio di MP, resta quello di partenza


def test_calibrated_wear_limit_is_used_and_kept_increasing():
    tarate = {"usura": [[0.02, "Near Mint"], [None, "Slightly Played"]]}
    limiti, tarato = cf._limiti_usura(tarate)
    assert tarato and limiti[0] == (0.02, "Near Mint")
    assert [l for l, _ in limiti] == sorted(l for l, _ in limiti)


def test_calibrated_foil_threshold_changes_the_answer():
    import random
    random.seed(3)
    ref = _carta_finta()
    rev = ref.copy()
    d = ImageDraw.Draw(rev)
    for _ in range(600):
        x, y = random.randint(50, 580), random.randint(510, 760)
        d.rectangle((x, y, x + 4, y + 4), fill=random.choice([(255, 255, 255), (90, 90, 90)]))
    misura = cf.foil(rev, ref, "pokemon")["score"]
    tarate = {"foil": {"pokemon": {"si": misura - 0.01, "no": misura - 0.2}}}
    r = cf.foil(rev, ref, "pokemon", tarate)
    assert r["value"] is True and r["calibrated"] is True
