-- Aggiunge metadati di sincronizzazione con eBay alla tabella articles.
-- Database: PostgreSQL

CREATE TYPE ebay_status AS ENUM ('NOT_LISTED', 'LISTED', 'SOLD');

ALTER TABLE articles
    ADD COLUMN IF NOT EXISTS ebay_status ebay_status NOT NULL DEFAULT 'NOT_LISTED',
    ADD COLUMN IF NOT EXISTS ebay_url VARCHAR(500),
    ADD COLUMN IF NOT EXISTS ebay_synced_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_articles_ebay_status ON articles(ebay_status);

COMMENT ON COLUMN articles.ebay_status IS
    'Stato sincronizzazione con eBay: NOT_LISTED (non pubblicato), LISTED (online), SOLD (venduto su eBay)';
COMMENT ON COLUMN articles.ebay_url IS
    'URL del listing su ebay.it (popolato manualmente dopo la pubblicazione)';
COMMENT ON COLUMN articles.ebay_synced_at IS
    'Ultimo aggiornamento manuale dello stato eBay';
