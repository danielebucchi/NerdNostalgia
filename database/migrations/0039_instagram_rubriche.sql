-- Rubriche Instagram (utils/instagram_rubriche.py).
-- Gli articoli di ogni post: chi commenta LISTA riceve i loro link in DM.
ALTER TABLE instagram_media ADD COLUMN article_ids TEXT NOT NULL DEFAULT '';
ALTER TABLE instagram_media ADD COLUMN rubrica VARCHAR(20);

-- I commenti a cui il bot ha gia' risposto in privato (una volta sola).
CREATE TABLE IF NOT EXISTS instagram_replies (
    comment_id VARCHAR(40) PRIMARY KEY,
    media_id VARCHAR(40) NOT NULL,
    replied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Storico dei valori di mercato delle carte, uno per rivalutazione: serve a
-- dire quali carte sono salite di piu'.
CREATE TABLE IF NOT EXISTS card_price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER NOT NULL REFERENCES personal_cards(id) ON DELETE CASCADE,
    value NUMERIC(10, 2) NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_card_price_history_card ON card_price_history(card_id, recorded_at);
