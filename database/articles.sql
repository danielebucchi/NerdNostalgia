-- Tabella Articles per NerdNostalgia
-- Database: PostgreSQL

-- Creazione tipo ENUM per la condizione dell'articolo
CREATE TYPE article_condition AS ENUM ('new', 'used', 'refurbished', 'for_parts');

-- Creazione tipo ENUM per lo stato dell'articolo
CREATE TYPE article_status AS ENUM ('draft', 'published', 'sold', 'archived');

-- Creazione tabella articles
CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'EUR',
    category VARCHAR(100),
    condition article_condition NOT NULL DEFAULT 'used',
    status article_status NOT NULL DEFAULT 'draft',
    quantity INTEGER NOT NULL DEFAULT 1,
    sku VARCHAR(100) UNIQUE,
    brand VARCHAR(100),
    model VARCHAR(100),
    weight_kg DECIMAL(8, 2),
    dimensions_cm VARCHAR(50),
    images JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP,
    sold_at TIMESTAMP,

    -- Foreign key verso tabella users
    CONSTRAINT fk_user
        FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

-- Indici per migliorare le performance delle query
CREATE INDEX idx_articles_user_id ON articles(user_id);
CREATE INDEX idx_articles_status ON articles(status);
CREATE INDEX idx_articles_category ON articles(category);
CREATE INDEX idx_articles_condition ON articles(condition);
CREATE INDEX idx_articles_sku ON articles(sku);
CREATE INDEX idx_articles_created_at ON articles(created_at DESC);
CREATE INDEX idx_articles_price ON articles(price);

-- Indice GIN per ricerca full-text su titolo e descrizione
CREATE INDEX idx_articles_search ON articles USING GIN (
    to_tsvector('italian', COALESCE(title, '') || ' ' || COALESCE(description, ''))
);

-- Trigger per aggiornare automaticamente updated_at
CREATE TRIGGER update_articles_updated_at
    BEFORE UPDATE ON articles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Commenti sulle colonne
COMMENT ON TABLE articles IS 'Tabella articoli da vendere su piattaforme e-commerce';
COMMENT ON COLUMN articles.id IS 'ID univoco articolo';
COMMENT ON COLUMN articles.user_id IS 'ID utente proprietario dell''articolo';
COMMENT ON COLUMN articles.title IS 'Titolo/nome dell''articolo';
COMMENT ON COLUMN articles.description IS 'Descrizione dettagliata dell''articolo';
COMMENT ON COLUMN articles.price IS 'Prezzo di vendita';
COMMENT ON COLUMN articles.currency IS 'Valuta (EUR, USD, etc)';
COMMENT ON COLUMN articles.category IS 'Categoria prodotto';
COMMENT ON COLUMN articles.condition IS 'Condizione: new, used, refurbished, for_parts';
COMMENT ON COLUMN articles.status IS 'Stato: draft, published, sold, archived';
COMMENT ON COLUMN articles.quantity IS 'Quantita disponibile';
COMMENT ON COLUMN articles.sku IS 'Codice prodotto univoco (Stock Keeping Unit)';
COMMENT ON COLUMN articles.brand IS 'Marca del prodotto';
COMMENT ON COLUMN articles.model IS 'Modello del prodotto';
COMMENT ON COLUMN articles.weight_kg IS 'Peso in chilogrammi';
COMMENT ON COLUMN articles.dimensions_cm IS 'Dimensioni in cm (es: 10x20x30)';
COMMENT ON COLUMN articles.images IS 'Array JSON di URL immagini';
COMMENT ON COLUMN articles.metadata IS 'Metadati aggiuntivi in formato JSON';
COMMENT ON COLUMN articles.created_at IS 'Data e ora di creazione';
COMMENT ON COLUMN articles.updated_at IS 'Data e ora ultimo aggiornamento';
COMMENT ON COLUMN articles.published_at IS 'Data e ora di pubblicazione';
COMMENT ON COLUMN articles.sold_at IS 'Data e ora di vendita';
