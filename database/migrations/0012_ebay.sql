-- Sync eBay (Inventory API) sugli articoli. ebay_synced_at esiste gia'
-- (tracking legacy) e viene riusato per l'ultimo push riuscito.
--   ebay_sku         = SKU inventory eBay (nostra chiave, es. NN-<id>).
--   ebay_offer_id    = id dell'offer creato (per update/withdraw).
--   ebay_listing_id  = id inserzione pubblicata (listingId).
ALTER TABLE articles ADD COLUMN ebay_sku VARCHAR(50);
ALTER TABLE articles ADD COLUMN ebay_offer_id VARCHAR(30);
ALTER TABLE articles ADD COLUMN ebay_listing_id VARCHAR(30);
