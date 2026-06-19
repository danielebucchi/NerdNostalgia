-- Aggiunge metadati di sincronizzazione con Vinted alla tabella articles.
-- Database: PostgreSQL

CREATE TYPE vinted_status AS ENUM ('NOT_LISTED', 'LISTED', 'SOLD');

ALTER TABLE articles
    ADD COLUMN IF NOT EXISTS vinted_status vinted_status NOT NULL DEFAULT 'NOT_LISTED',
    ADD COLUMN IF NOT EXISTS vinted_url VARCHAR(500),
    ADD COLUMN IF NOT EXISTS vinted_synced_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_articles_vinted_status ON articles(vinted_status);

COMMENT ON COLUMN articles.vinted_status IS
    'Stato sincronizzazione con Vinted: NOT_LISTED (non pubblicato), LISTED (online), SOLD (venduto su Vinted)';
COMMENT ON COLUMN articles.vinted_url IS
    'URL del listing su vinted.it (popolato manualmente dopo la pubblicazione)';
COMMENT ON COLUMN articles.vinted_synced_at IS
    'Ultimo aggiornamento manuale dello stato Vinted';
