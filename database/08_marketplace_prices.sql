-- Prezzi specifici per marketplace (commissioni e dinamiche differenti).
-- Database: PostgreSQL

ALTER TABLE articles
    ADD COLUMN IF NOT EXISTS vinted_price DECIMAL(10, 2),
    ADD COLUMN IF NOT EXISTS ebay_price   DECIMAL(10, 2);

COMMENT ON COLUMN articles.vinted_price IS
    'Prezzo specifico su Vinted (NULL = usa price principale)';
COMMENT ON COLUMN articles.ebay_price IS
    'Prezzo specifico su eBay (NULL = usa price principale)';
