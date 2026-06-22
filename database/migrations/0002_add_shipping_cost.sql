-- Aggiunge shipping_price agli articoli: costo della spedizione mostrato
-- al cliente e sommato al price nel link PayPal sul sito.
--
-- NB: e' diverso dal campo shipping_cost gia' esistente, che e' la spesa
-- sostenuta lato venditore per il tracking interno profit/loss (potrebbe
-- includere ricarico/sconto rispetto a quanto si fa pagare al cliente).
--
-- NULL = "spedizione da concordare" → nel link PayPal viene trattato come 0
-- e il bottone mostra una nota "+ spedizione" come avviso.

ALTER TABLE articles ADD COLUMN shipping_price NUMERIC(10, 2);
