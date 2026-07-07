-- Prezzo di listino sull'inventory_item: quanto voglio esporre l'articolo
-- sul catalogo pubblico quando lo pubblico. Separato da sale_price, che e'
-- il ricavo effettivo a vendita conclusa.
--
-- Al publish_to_site l'Article eredita:
--   Article.price = item.list_price ?? item.sale_price ?? 0

ALTER TABLE inventory_items ADD COLUMN list_price NUMERIC(10, 2);
