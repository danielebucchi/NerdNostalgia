-- Backfill: tutti gli articoli con shipping_price NULL → 5.00.
-- SQLite non supporta ALTER COLUMN per cambiare il DEFAULT esistente,
-- quindi il DEFAULT in schema.sql vale solo per DB nuovi. Per quelli gia'
-- creati da 0002 (senza DEFAULT) facciamo il backfill esplicito.
UPDATE articles SET shipping_price = 5.00 WHERE shipping_price IS NULL;
