-- Tabella Wanted Items (cerco/compro) per NerdNostalgia
-- Database: PostgreSQL

CREATE TYPE wanted_status AS ENUM ('ACTIVE', 'FULFILLED', 'CLOSED');

CREATE TABLE IF NOT EXISTS wanted_items (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    brand VARCHAR(100),
    model VARCHAR(100),
    preferred_condition article_condition,
    max_price DECIMAL(10, 2),
    currency VARCHAR(3) DEFAULT 'EUR',
    notes TEXT,
    status wanted_status NOT NULL DEFAULT 'ACTIVE',
    priority INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fulfilled_at TIMESTAMP
);

CREATE INDEX idx_wanted_status ON wanted_items(status);
CREATE INDEX idx_wanted_category ON wanted_items(category);
CREATE INDEX idx_wanted_priority ON wanted_items(priority DESC);
CREATE INDEX idx_wanted_created_at ON wanted_items(created_at DESC);

CREATE INDEX idx_wanted_search ON wanted_items USING GIN (
    to_tsvector('italian', COALESCE(title, '') || ' ' || COALESCE(description, ''))
);

CREATE TRIGGER update_wanted_updated_at
    BEFORE UPDATE ON wanted_items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE wanted_items IS 'Sezione "cerco/compro": articoli che l''admin desidera acquistare';
COMMENT ON COLUMN wanted_items.preferred_condition IS 'Condizione preferita (NEW/USED/...). NULL = qualsiasi';
COMMENT ON COLUMN wanted_items.max_price IS 'Offerta massima indicativa. NULL = da concordare';
COMMENT ON COLUMN wanted_items.priority IS 'Ordinamento: piu alto = prima';
COMMENT ON COLUMN wanted_items.status IS 'ACTIVE = sto cercando, FULFILLED = trovato, CLOSED = non cerco piu';
