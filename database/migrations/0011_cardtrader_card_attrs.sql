-- Attributi carta rilevanti per CardTrader (condizione, lingua, reverse,
-- prima edizione). Servono a:
--   1. pubblicare il prodotto con le properties giuste (condition,
--      pokemon_language, pokemon_reverse, first_edition);
--   2. calcolare il prezzo "4° piu' basso" SOLO fra inserzioni comparabili
--      (stessa condizione + lingua + reverse + prima edizione).
-- Persistiti sia sull'item (sorgente) sia sull'articolo (cio' che va online).
-- card_language: codice CardTrader (en/fr/de/it/pt/es). NULL = default setting.
ALTER TABLE articles ADD COLUMN card_condition VARCHAR(30);
ALTER TABLE articles ADD COLUMN card_language VARCHAR(5);
ALTER TABLE articles ADD COLUMN card_reverse INTEGER NOT NULL DEFAULT 0;
ALTER TABLE articles ADD COLUMN card_first_edition INTEGER NOT NULL DEFAULT 0;

ALTER TABLE inventory_items ADD COLUMN card_condition VARCHAR(30);
ALTER TABLE inventory_items ADD COLUMN card_language VARCHAR(5);
ALTER TABLE inventory_items ADD COLUMN card_reverse INTEGER NOT NULL DEFAULT 0;
ALTER TABLE inventory_items ADD COLUMN card_first_edition INTEGER NOT NULL DEFAULT 0;
