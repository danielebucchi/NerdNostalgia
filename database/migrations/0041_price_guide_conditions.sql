-- Guida prezzi: i prezzi per condizione e lingua (italiana, inglese) di
-- ogni carta, {"it": {"NM": centesimi, ...}, "en": {...}}. Vedi utils/price_guide.py.
ALTER TABLE price_guide_cards ADD COLUMN prices TEXT;
