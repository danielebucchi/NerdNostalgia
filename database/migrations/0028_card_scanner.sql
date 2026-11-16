-- Scanner carte: coda degli scan da confermare, indice locale dei
-- blueprint CardTrader, e sulla collezione (personal_cards) l'abbinamento
-- al catalogo, i prezzi di mercato e le inserzioni CardTrader/eBay.
--
-- Prima le tabelle nuove e poi le colonne: su un DB nato dallo schema.sql
-- aggiornato la prima ALTER fallisce con "duplicate column" e il runner
-- ferma lo script li' — le tabelle a quel punto ci sono gia'.
CREATE TABLE IF NOT EXISTS card_scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_url VARCHAR(500) NOT NULL,
    original_filename VARCHAR(255),
    game_id INTEGER,
    expansion_id INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','CONFIRMED','DISCARDED')),
    ocr JSON NOT NULL DEFAULT '{}',
    candidates JSON NOT NULL DEFAULT '[]',
    confidence VARCHAR(10),
    error TEXT,
    personal_card_id INTEGER REFERENCES personal_cards(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_card_scans_status ON card_scans(status);

CREATE TABLE IF NOT EXISTS card_blueprints (
    id BIGINT PRIMARY KEY,
    game_id INTEGER NOT NULL,
    expansion_id INTEGER NOT NULL,
    expansion_code VARCHAR(30),
    expansion_name VARCHAR(200),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(255),
    collector_number VARCHAR(50),
    number_norm VARCHAR(50),
    image_url VARCHAR(500),
    dhash VARCHAR(64),
    indexed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_card_blueprints_game_number ON card_blueprints(game_id, number_norm);
CREATE INDEX IF NOT EXISTS idx_card_blueprints_expansion ON card_blueprints(expansion_id);
CREATE INDEX IF NOT EXISTS idx_card_blueprints_code ON card_blueprints(expansion_code);

ALTER TABLE personal_cards ADD COLUMN game_id INTEGER;
ALTER TABLE personal_cards ADD COLUMN printed_code VARCHAR(50);
ALTER TABLE personal_cards ADD COLUMN cardtrader_blueprint_id BIGINT;
ALTER TABLE personal_cards ADD COLUMN cardtrader_expansion_id INTEGER;
ALTER TABLE personal_cards ADD COLUMN reverse BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE personal_cards ADD COLUMN first_edition BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE personal_cards ADD COLUMN cardtrader_price NUMERIC(10,2);
ALTER TABLE personal_cards ADD COLUMN cardtrader_offers INTEGER;
ALTER TABLE personal_cards ADD COLUMN ebay_sold_avg NUMERIC(10,2);
ALTER TABLE personal_cards ADD COLUMN ebay_sold_count INTEGER;
ALTER TABLE personal_cards ADD COLUMN ebay_sold JSON;
ALTER TABLE personal_cards ADD COLUMN ebay_sold_source VARCHAR(20);
ALTER TABLE personal_cards ADD COLUMN prices_updated_at TIMESTAMP;
ALTER TABLE personal_cards ADD COLUMN list_price NUMERIC(10,2);
ALTER TABLE personal_cards ADD COLUMN cardtrader_product_id BIGINT;
ALTER TABLE personal_cards ADD COLUMN cardtrader_synced_at TIMESTAMP;
ALTER TABLE personal_cards ADD COLUMN ebay_sku VARCHAR(50);
ALTER TABLE personal_cards ADD COLUMN ebay_offer_id VARCHAR(30);
ALTER TABLE personal_cards ADD COLUMN ebay_listing_id VARCHAR(30);
ALTER TABLE personal_cards ADD COLUMN ebay_synced_at TIMESTAMP;
CREATE INDEX IF NOT EXISTS idx_personal_cards_blueprint ON personal_cards(cardtrader_blueprint_id);
