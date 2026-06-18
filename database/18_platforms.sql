-- Tabella platforms: lista unificata per acquisti e vendite.
-- Sostituisce le costanti hardcoded nei form admin.
-- PostgreSQL. Idempotente.

CREATE TABLE IF NOT EXISTS platforms (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    icon VARCHAR(10),
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_platforms_slug ON platforms(slug);
CREATE INDEX IF NOT EXISTS idx_platforms_active ON platforms(is_active);
CREATE INDEX IF NOT EXISTS idx_platforms_order ON platforms(display_order);

DROP TRIGGER IF EXISTS update_platforms_updated_at ON platforms;
CREATE TRIGGER update_platforms_updated_at
    BEFORE UPDATE ON platforms
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Seed iniziale con le piattaforme attualmente hardcoded
INSERT INTO platforms (name, slug, icon, display_order, is_active) VALUES
    ('Vinted', 'vinted', '🛍', 10, TRUE),
    ('eBay', 'ebay', '🅔', 20, TRUE),
    ('mercato', 'mercato', '🏪', 30, TRUE),
    ('Subito', 'subito', '📱', 40, TRUE),
    ('Wallapop', 'wallapop', '💬', 50, TRUE),
    ('CardTrader', 'cardtrader', '🎴', 60, TRUE),
    ('Privato', 'privato', '👤', 70, TRUE),
    ('Regalo', 'regalo', '🎁', 80, TRUE),
    ('Altro', 'altro', '…', 90, TRUE)
ON CONFLICT (slug) DO NOTHING;

COMMENT ON TABLE platforms IS 'Piattaforme unificate: stesso elenco per acquisti e vendite.';
COMMENT ON COLUMN platforms.is_active IS 'FALSE = nascosta dai dropdown ma non cancellata (preserva storico)';
