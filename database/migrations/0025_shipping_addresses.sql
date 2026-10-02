-- Rubrica degli indirizzi di spedizione del cliente.
--
-- Finora l'indirizzo viveva solo dentro l'ordine: ogni acquisto voleva
-- dire riscrivere via, CAP, citta' e telefono da capo, anche per chi
-- compra ogni mese dallo stesso posto.
--
-- Gli ordini NON puntano qui: continuano a tenersi la loro copia dei campi
-- ship_*. Se il cliente cancella un indirizzo o lo corregge dopo il
-- trasloco, gli ordini vecchi devono restare con l'indirizzo a cui il
-- pacco e' partito davvero — serve a ricostruire una consegna contestata.
CREATE TABLE IF NOT EXISTS shipping_addresses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Come lo chiama il cliente ("Casa", "Ufficio"). Facoltativo: se non
    -- lo mette, in elenco si legge comunque la via.
    label VARCHAR(60),

    -- Il destinatario puo' non essere l'intestatario dell'account: si
    -- spedisce anche a un regalo, a un parente, a un collega.
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(50),

    street VARCHAR(255) NOT NULL,
    city VARCHAR(120) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    province VARCHAR(120),
    country VARCHAR(80) NOT NULL DEFAULT 'Italia',

    -- Quello proposto al checkout. Ne resta uno solo acceso per utente:
    -- ci pensa l'applicazione, SQLite non ha indici parziali su cui
    -- appoggiarsi in modo portabile.
    is_default BOOLEAN NOT NULL DEFAULT 0,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_shipping_addresses_user
    ON shipping_addresses(user_id);
