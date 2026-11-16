-- Scanner carte che impara dalle conferme: gli scan confermati diventano
-- riferimenti per riconoscere la stessa carta, le correzioni insegnano le
-- confusioni dell'OCR. Prima le tabelle, poi la colonna (vedi 0028); gli indici sulle tabelle gia esistenti stanno nelle migrazioni, non in schema.sql (vedi 0031).
CREATE TABLE IF NOT EXISTS card_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blueprint_id BIGINT NOT NULL,
    game_id INTEGER NOT NULL,
    dhash VARCHAR(64) NOT NULL,
    scan_id INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_card_references_game ON card_references(game_id);
CREATE INDEX IF NOT EXISTS idx_card_references_blueprint ON card_references(blueprint_id);

CREATE TABLE IF NOT EXISTS ocr_corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER,
    kind VARCHAR(10) NOT NULL,
    read_text VARCHAR(50) NOT NULL,
    true_text VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ocr_corrections_game ON ocr_corrections(game_id);

ALTER TABLE card_scans ADD COLUMN dhash VARCHAR(64);
