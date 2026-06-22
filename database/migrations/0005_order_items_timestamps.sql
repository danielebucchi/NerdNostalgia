-- order_items eredita created_at/updated_at da BaseModel (SQLAlchemy)
-- ma la migrazione 0004 non li aveva. Backfill: aggiungiamo le colonne
-- con default CURRENT_TIMESTAMP.

ALTER TABLE order_items ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE order_items ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
