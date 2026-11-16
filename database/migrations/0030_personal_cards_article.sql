-- Scanner carte: la carta della collezione puo' essere in vendita anche
-- sul sito, tramite un articolo (gli ordini passano dagli articoli).
ALTER TABLE personal_cards ADD COLUMN article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_personal_cards_article ON personal_cards(article_id);
