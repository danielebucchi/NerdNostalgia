-- Indice su ebay_group_key (0033). Sta qui e non in schema.sql: schema.sql
-- gira prima delle migrazioni, e su un DB gia' esistente personal_cards non
-- ha ancora la colonna. Su un DB nuovo la 0033 e' un no-op (colonna gia'
-- creata da schema.sql) e l'indice non lo creerebbe nessuno.
CREATE INDEX IF NOT EXISTS idx_personal_cards_ebay_group ON personal_cards(ebay_group_key);
