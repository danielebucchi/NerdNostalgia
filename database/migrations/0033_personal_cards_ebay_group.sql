-- eBay: piu' carte in un'unica inserzione con varianti ("scegli la carta").
-- La carta ricorda il gruppo (inventory item group) di cui e' una voce;
-- le carte di uno stesso gruppo condividono l'ebay_listing_id.
ALTER TABLE personal_cards ADD COLUMN ebay_group_key VARCHAR(50);
CREATE INDEX IF NOT EXISTS idx_personal_cards_ebay_group ON personal_cards(ebay_group_key);
