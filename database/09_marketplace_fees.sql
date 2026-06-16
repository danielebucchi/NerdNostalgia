-- Mappa categoria -> markup percentuale per marketplace, modificabile
-- dall'admin via UI.
-- Database: PostgreSQL

CREATE TABLE IF NOT EXISTS marketplace_fees (
    id SERIAL PRIMARY KEY,
    marketplace VARCHAR(50) NOT NULL,
    category VARCHAR(100),
    markup_percent DECIMAL(5, 2) NOT NULL,
    note VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_marketplace_fees_lookup
    ON marketplace_fees(marketplace, category);

CREATE TRIGGER update_marketplace_fees_updated_at
    BEFORE UPDATE ON marketplace_fees
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE marketplace_fees IS
    'Markup percentuali per marketplace e categoria. category NULL = default per quel marketplace';
COMMENT ON COLUMN marketplace_fees.markup_percent IS
    'Percentuale di maggiorazione da applicare sul prezzo catalogo';

-- Seed con i preset attualmente hardcoded nel frontend
INSERT INTO marketplace_fees (marketplace, category, markup_percent, note) VALUES
    ('ebay',   NULL,             11.00, 'default'),
    ('ebay',   'videogames',     10.00, 'commissione standard videogame'),
    ('ebay',   'videogames',     11.00, 'safety margin'),
    ('ebay',   'pokemon-cards',  12.00, 'final value fee carte da collezione'),
    ('ebay',   'pokemon-cards',  13.00, 'safety margin carte rare'),
    ('ebay',   'funko-pop',      12.00, 'commissione standard collezionismo'),
    ('ebay',   'books',          10.00, 'libri / riviste'),
    ('ebay',   'fashion',        17.00, 'commissione moda'),
    ('vinted', NULL,             0.00,  'fee a carico buyer'),
    ('vinted', NULL,             5.00,  'cuscinetto');
