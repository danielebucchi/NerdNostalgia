-- Tabelle per la sync giornaliera dal profilo Vinted:
--   * vinted_category_mappings → mappa catalog Vinted → categoria NN
--   * vinted_sync_logs         → storico runs (count, errori)
--   * vinted_settings          → configurazione (user_id Vinted, intervallo)
-- Database: PostgreSQL. Idempotente.

-- ---------------------------------------------------------------------------
-- 1) vinted_settings: configurazione globale (riga singola)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vinted_settings (
    id SERIAL PRIMARY KEY,
    vinted_user_id BIGINT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    sync_hour INTEGER NOT NULL DEFAULT 4,
    last_run_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

DROP TRIGGER IF EXISTS update_vinted_settings_updated_at ON vinted_settings;
CREATE TRIGGER update_vinted_settings_updated_at
    BEFORE UPDATE ON vinted_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE vinted_settings IS 'Configurazione sync Vinted: user_id del profilo + scheduling';

-- Seed iniziale: profilo dell'utente (Cate 95521831)
INSERT INTO vinted_settings (vinted_user_id, enabled, sync_hour)
SELECT 95521831, TRUE, 4
WHERE NOT EXISTS (SELECT 1 FROM vinted_settings);

-- NOTA: la tabella vinted_category_mappings e' stata rimossa (NN-016).
-- Vinted nelle response del profilo non espone catalog_id, quindi le
-- categorie vengono assegnate via keyword detection in
-- backend/utils/vinted_sync.py::CATEGORY_RULES.
DROP TABLE IF EXISTS vinted_category_mappings;

-- ---------------------------------------------------------------------------
-- 2) vinted_sync_logs: storico delle sync
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vinted_sync_logs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    triggered_by VARCHAR(20) NOT NULL DEFAULT 'cron',
    items_fetched INTEGER NOT NULL DEFAULT 0,
    items_imported INTEGER NOT NULL DEFAULT 0,
    items_updated INTEGER NOT NULL DEFAULT 0,
    items_skipped INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Per installazioni preesistenti dove le colonne mancano:
ALTER TABLE vinted_sync_logs
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_vinted_logs_started
    ON vinted_sync_logs(started_at DESC);

COMMENT ON TABLE vinted_sync_logs IS
    'Storico di tutte le esecuzioni di sync (cron + manuali)';
COMMENT ON COLUMN vinted_sync_logs.triggered_by IS
    'cron = scheduler giornaliero, manual = bottone da admin';

-- ---------------------------------------------------------------------------
-- 4) articles: link 1:1 con il listing Vinted (per dedupe)
-- ---------------------------------------------------------------------------
ALTER TABLE articles
    ADD COLUMN IF NOT EXISTS vinted_item_id BIGINT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_articles_vinted_item
    ON articles(vinted_item_id)
    WHERE vinted_item_id IS NOT NULL;

COMMENT ON COLUMN articles.vinted_item_id IS
    'ID Vinted del listing originale. Usato dalla sync per dedupe.';
