-- Opzione "Scambio a mano" sull'ordine: se attiva e l'indirizzo e' in
-- provincia di Livorno (CAP 57xxx) o Pisa (CAP 56xxx), la spedizione e' 0.

ALTER TABLE orders ADD COLUMN hand_exchange BOOLEAN NOT NULL DEFAULT 0;
