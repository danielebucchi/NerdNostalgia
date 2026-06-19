-- Aggiunge tracciamento vendite a personal_cards.
-- Use case: carte comprate al kg (costo bulk) e rivendute singolarmente.
-- PostgreSQL. Idempotente.

ALTER TABLE personal_cards ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'IN_STOCK';
ALTER TABLE personal_cards ADD COLUMN IF NOT EXISTS sold_date DATE;
ALTER TABLE personal_cards ADD COLUMN IF NOT EXISTS sold_by VARCHAR(20);
ALTER TABLE personal_cards ADD COLUMN IF NOT EXISTS sold_platform VARCHAR(50);
ALTER TABLE personal_cards ADD COLUMN IF NOT EXISTS sale_price DECIMAL(10, 2);
ALTER TABLE personal_cards ADD COLUMN IF NOT EXISTS fee_amount DECIMAL(10, 2);
ALTER TABLE personal_cards ADD COLUMN IF NOT EXISTS shipping_cost DECIMAL(10, 2);
ALTER TABLE personal_cards ADD COLUMN IF NOT EXISTS bulk_source VARCHAR(100);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'personal_cards_status_check'
    ) THEN
        ALTER TABLE personal_cards
            ADD CONSTRAINT personal_cards_status_check
            CHECK (status IN ('IN_STOCK','RESERVED','SOLD','ARCHIVED'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_personal_cards_status ON personal_cards(status);
CREATE INDEX IF NOT EXISTS idx_personal_cards_sold_date ON personal_cards(sold_date DESC);

COMMENT ON COLUMN personal_cards.bulk_source IS 'Origine bulk: es. "Acquisto kg aprile" — gruppo per costo medio';
COMMENT ON COLUMN personal_cards.status IS 'IN_STOCK / RESERVED / SOLD / ARCHIVED';
COMMENT ON TABLE personal_cards IS 'Carte sciolte (no flipping): comprate al kg, vendute singolarmente';
