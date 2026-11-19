-- Scanner carte: nome della carta e del set in italiano (TCGdex, Scryfall,
-- YGOPRODeck). CardTrader li ha solo in inglese; per le carte italiane i
-- titoli usano questi, che sono quelli stampati e cercati dai compratori.
ALTER TABLE personal_cards ADD COLUMN name_it VARCHAR(200);
ALTER TABLE personal_cards ADD COLUMN collection_it VARCHAR(100);
