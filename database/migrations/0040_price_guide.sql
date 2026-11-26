-- Guida prezzi delle carte Pokémon (utils/price_guide.py): un set e una
-- carta per pagina pubblica, prezzi CardTrader aggiornati ogni settimana.
CREATE TABLE IF NOT EXISTS price_guide_sets (
    id INTEGER PRIMARY KEY,                  -- id dell'espansione CardTrader
    slug VARCHAR(120) NOT NULL UNIQUE,
    name_en VARCHAR(200) NOT NULL,
    name_it VARCHAR(200),
    tcgdex_id VARCHAR(40),
    release_date VARCHAR(10),
    card_count INTEGER,
    serie VARCHAR(120),
    logo_url VARCHAR(500),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS price_guide_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    set_id INTEGER NOT NULL REFERENCES price_guide_sets(id) ON DELETE CASCADE,
    blueprint_id INTEGER NOT NULL UNIQUE,
    number VARCHAR(20) NOT NULL,
    slug VARCHAR(160) NOT NULL,
    name_en VARCHAR(200) NOT NULL,
    name_it VARCHAR(200),
    image_url VARCHAR(500),
    min_price_cents INTEGER,
    offers INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (set_id, slug)
);
CREATE INDEX IF NOT EXISTS idx_price_guide_cards_set ON price_guide_cards(set_id);
CREATE INDEX IF NOT EXISTS idx_price_guide_cards_name ON price_guide_cards(name_en);
