-- Aggiunge display_order per ordinamento manuale del catalogo articoli.
-- Database: PostgreSQL

ALTER TABLE articles
    ADD COLUMN IF NOT EXISTS display_order INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_articles_display_order
    ON articles(display_order ASC, created_at DESC);

COMMENT ON COLUMN articles.display_order IS
    'Ordinamento manuale del catalogo: piu basso = prima in vetrina';
