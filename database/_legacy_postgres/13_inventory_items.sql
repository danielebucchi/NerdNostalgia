-- Tabella inventory_items: clone 1:1 del foglio "Flipping Inventario" +
-- "Carte Pokemon Inventario" del Google Sheet di gestione interna.
--
-- Filosofia: standalone, scollegata dal catalogo pubblico. Un item PUO'
-- avere un article_id (FK opzionale) se viene pubblicato sul sito, ma di
-- default e' solo tracking interno.
-- Database: PostgreSQL. Idempotente.

CREATE TABLE IF NOT EXISTS inventory_items (
    id SERIAL PRIMARY KEY,

    -- Identificativi
    lotto VARCHAR(50),
    title VARCHAR(500) NOT NULL,
    description TEXT,

    -- Acquisto
    purchase_date DATE,
    cost DECIMAL(10, 2),
    purchase_platform VARCHAR(50),
    bought_by VARCHAR(20),

    -- Vendita
    sold_date DATE,
    sold_by VARCHAR(20),
    sold_platform VARCHAR(50),
    sale_price DECIMAL(10, 2),
    fee_amount DECIMAL(10, 2),
    shipping_cost DECIMAL(10, 2),

    -- Stato
    listed BOOLEAN NOT NULL DEFAULT FALSE,
    quantity INTEGER NOT NULL DEFAULT 1,
    quantity_sold INTEGER NOT NULL DEFAULT 0,

    -- Categoria (opzionale)
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,

    -- Campi specifici carte (Pokemon/Magic/ecc)
    card_collection VARCHAR(100),
    card_number VARCHAR(50),
    card_finish VARCHAR(50),

    -- Link opzionali esterni
    article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
    vinted_item_id BIGINT,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_inventory_lotto ON inventory_items(lotto);
CREATE INDEX IF NOT EXISTS idx_inventory_purchase_date ON inventory_items(purchase_date DESC);
CREATE INDEX IF NOT EXISTS idx_inventory_sold_date ON inventory_items(sold_date DESC);
CREATE INDEX IF NOT EXISTS idx_inventory_category ON inventory_items(category_id);
CREATE INDEX IF NOT EXISTS idx_inventory_article ON inventory_items(article_id);

DROP TRIGGER IF EXISTS update_inventory_items_updated_at ON inventory_items;
CREATE TRIGGER update_inventory_items_updated_at
    BEFORE UPDATE ON inventory_items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE inventory_items IS
    'Gestione interna lotti: clone Flipping Inventario. Indipendente dal catalogo pubblico.';
COMMENT ON COLUMN inventory_items.article_id IS
    'NULL = solo tracking interno. Se valorizzato, l''item e'' pubblicato sul sito.';
COMMENT ON COLUMN inventory_items.listed IS
    'TRUE se attivamente listato (su Vinted o sul sito). Equivalente colonna "Listato" del foglio.';
