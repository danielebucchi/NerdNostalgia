-- Iscrizioni "avvisami dei nuovi arrivi": email + categoria (NULL = tutte).
-- Quando un articolo passa a PUBLISHED viene mandata una mail agli iscritti
-- della sua categoria (e agli iscritti "tutte"). Disiscrizione via link con
-- token HMAC, nessun account richiesto.

CREATE TABLE IF NOT EXISTS category_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) NOT NULL,
    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (email, category_id)
);
CREATE INDEX IF NOT EXISTS idx_category_alerts_category
    ON category_alerts(category_id);
