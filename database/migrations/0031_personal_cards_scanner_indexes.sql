-- Indici sulle colonne dello scanner carte (0028, 0030). Stanno qui e non
-- in schema.sql: schema.sql gira prima delle migrazioni, e su un DB gia'
-- esistente personal_cards non ha ancora quelle colonne.
CREATE INDEX IF NOT EXISTS idx_personal_cards_blueprint ON personal_cards(cardtrader_blueprint_id);
CREATE INDEX IF NOT EXISTS idx_personal_cards_article ON personal_cards(article_id);
