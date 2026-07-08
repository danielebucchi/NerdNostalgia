-- Tabella settings chiave/valore per configurazione runtime.
--
-- Sostituisce le env NEXT_PUBLIC_* bake-ate al build-time del frontend:
-- i valori qui si cambiano da /admin/impostazioni SENZA rebuild Docker.
-- Il frontend legge le chiavi pubbliche via GET /api/settings/public;
-- la whitelist di cosa e' pubblico vive nel backend (api/settings.py),
-- non nel DB, cosi' non si puo' esporre un segreto per errore di flag.

CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
