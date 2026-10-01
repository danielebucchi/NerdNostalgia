-- Quota fissa nelle commissioni.
--
-- Finora il markup era solo percentuale, e bastava per Vinted/eBay. Non basta
-- per i gateway di pagamento: PayPal e Stripe applicano percentuale PIU' una
-- quota fissa a transazione. Su un articolo da 8 euro la parte fissa pesa piu'
-- della percentuale, quindi con la sola % il prezzo di vendita esce sotto.
ALTER TABLE marketplace_fees ADD COLUMN fixed_fee NUMERIC(10,2) NOT NULL DEFAULT 0;
