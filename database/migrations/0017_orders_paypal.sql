-- Pagamento con i bottoni PayPal ufficiali (Orders v2).
--   paypal_order_id   = ordine creato su PayPal, serve a riprendere/catturare
--   paypal_capture_id = incasso effettivo, riferimento per riconciliare e
--                       per eventuali rimborsi
-- Niente indice: si cercano sempre partendo dal nostro ordine per chiave
-- primaria, e schema.sql gira prima delle migration (vedi 0015).
ALTER TABLE orders ADD COLUMN paypal_order_id VARCHAR(64);
ALTER TABLE orders ADD COLUMN paypal_capture_id VARCHAR(64);
