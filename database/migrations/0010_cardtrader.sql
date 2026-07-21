-- Abbinamento e sync CardTrader sugli articoli.
--   cardtrader_blueprint_id  = voce di catalogo CardTrader (scelta 1 volta
--                              via ricerca assistita in admin). NULL = carta
--                              non abbinata → non sincronizzabile.
--   cardtrader_product_id    = id del prodotto creato sul nostro shop (per
--                              update/delete). NULL = non ancora pubblicato.
--   cardtrader_synced_at     = ultimo push riuscito.
ALTER TABLE articles ADD COLUMN cardtrader_blueprint_id BIGINT;
ALTER TABLE articles ADD COLUMN cardtrader_product_id BIGINT;
ALTER TABLE articles ADD COLUMN cardtrader_synced_at TIMESTAMP;
