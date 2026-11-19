"""Catalogo pubblico lato server: pagina + conteggi dei filtri.

Le regole sono quelle che prima giravano nel browser (CatalogSection.tsx):
qui si controlla che i numeri restino quelli."""
import pytest

from models.db import Article, ArticleCondition, ArticleStatus, Category


@pytest.fixture()
def catalogo(db_session, admin_user):
    carte = Category(name="Carte", slug="carte-c")
    giochi = Category(name="Videogiochi", slug="videogiochi-c")
    db_session.add_all([carte, giochi])
    db_session.flush()
    poke = Category(name="Pokémon", slug="pokemon-c", parent_id=carte.id)
    db_session.add(poke)
    db_session.flush()

    def art(titolo, prezzo, cat, cond=ArticleCondition.USED, brand=None, stato=ArticleStatus.PUBLISHED):
        a = Article(user_id=admin_user.id, title=titolo, price=prezzo, condition=cond,
                    status=stato, category_id=cat.id, brand=brand)
        db_session.add(a)
        return a

    for i in range(30):
        art(f"Carta Pokemon {i:02d}", 1 + i, poke)
    art("Pichu liv 9 arceus", 4, poke)
    art("Super Mario 64", 40, giochi, cond=ArticleCondition.NEW, brand="Nintendo")
    art("Zelda Ocarina", 35, giochi, brand="Nintendo")
    art("Bozza nascosta", 5, giochi, stato=ArticleStatus.DRAFT)
    db_session.commit()
    return {"carte": carte, "giochi": giochi, "poke": poke}


def test_first_page_total_and_facets(client, catalogo):
    r = client.get("/api/articles/catalog")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["total"] == 33 and len(d["items"]) == 24          # una pagina, non tutto
    f = d["facets"]
    assert f["categories"]["carte-c"] == {"name": "Carte", "count": 31}
    assert f["categories"]["videogiochi-c"]["count"] == 2
    assert f["total_all_categories"] == 33
    assert f["conditions"] == {"NEW": 1, "USED": 32}
    assert f["brands"] == {"Nintendo": 2}
    assert (f["price_min"], f["price_max"]) == (1, 40)
    # La pagina dopo
    assert len(client.get("/api/articles/catalog?skip=24").json()["items"]) == 9


def test_search_finds_old_articles_too(client, catalogo):
    """Il bug di partenza: un articolo vecchio non si trovava nel catalogo."""
    d = client.get("/api/articles/catalog?search=pichu").json()
    assert d["total"] == 1 and d["items"][0]["title"] == "Pichu liv 9 arceus"


def test_counts_exclude_their_own_dimension(client, catalogo):
    d = client.get("/api/articles/catalog?category=videogiochi-c").json()
    assert d["total"] == 2
    # Le altre categorie si contano come se il filtro categoria non ci fosse
    assert d["facets"]["categories"]["carte-c"]["count"] == 31
    assert d["facets"]["conditions"] == {"NEW": 1, "USED": 1}


def test_subcategories_appear_under_the_chosen_category(client, catalogo):
    d = client.get("/api/articles/catalog?category=carte-c").json()
    assert d["facets"]["subcategories"] == {"pokemon-c": {"name": "Pokémon", "count": 31}}
    assert d["facets"]["total_all_subcategories"] == 31


def test_sort_and_price_range(client, catalogo):
    d = client.get("/api/articles/catalog?sort=price_desc&min_price=30&max_price=40").json()
    assert [a["title"] for a in d["items"]] == ["Super Mario 64", "Zelda Ocarina", "Carta Pokemon 29"]
