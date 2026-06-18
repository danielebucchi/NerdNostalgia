-- Collezione carte personale (NO flipping).
-- Tabella separata da inventory_items: queste carte NON sono in vendita,
-- NON entrano nei bilanci del flipping, sono tracking personale.
-- PostgreSQL. Idempotente.

CREATE TABLE IF NOT EXISTS personal_cards (
    id SERIAL PRIMARY KEY,

    name VARCHAR(200) NOT NULL,
    collection VARCHAR(100),
    card_number VARCHAR(50),
    finish VARCHAR(50),
    language VARCHAR(20) DEFAULT 'IT',
    condition VARCHAR(20),
    grading VARCHAR(20),

    owned_by VARCHAR(20),
    quantity INTEGER NOT NULL DEFAULT 1,

    purchase_date DATE,
    purchase_cost DECIMAL(10, 2),
    purchase_source VARCHAR(50),

    estimated_value DECIMAL(10, 2),
    estimated_value_updated_at DATE,

    images JSONB NOT NULL DEFAULT '[]'::jsonb,
    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_personal_cards_owned_by ON personal_cards(owned_by);
CREATE INDEX IF NOT EXISTS idx_personal_cards_collection ON personal_cards(collection);
CREATE INDEX IF NOT EXISTS idx_personal_cards_purchase_date ON personal_cards(purchase_date DESC);

DROP TRIGGER IF EXISTS update_personal_cards_updated_at ON personal_cards;
CREATE TRIGGER update_personal_cards_updated_at
    BEFORE UPDATE ON personal_cards
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE personal_cards IS 'Collezione personale carte: NON in vendita, NON entra nei bilanci flipping';
COMMENT ON COLUMN personal_cards.purchase_source IS 'Dove acquistata: acquisto/regalo/booster/scambio/altro';
COMMENT ON COLUMN personal_cards.condition IS 'Condizione non gradata: NM/M/EX/LP/MP/HP/DMG';
COMMENT ON COLUMN personal_cards.grading IS 'Grading professionale: PSA 10, BGS 9.5, ecc';
