-- Scanner carte: un prezzo per piattaforma. NULL = calcolato (CardTrader
-- come il sito, eBay con commissioni e minimo di 1 euro); un valore lo
-- sostituisce solo su quella piattaforma.
ALTER TABLE personal_cards ADD COLUMN list_price_cardtrader NUMERIC(10,2);
ALTER TABLE personal_cards ADD COLUMN list_price_ebay NUMERIC(10,2);
