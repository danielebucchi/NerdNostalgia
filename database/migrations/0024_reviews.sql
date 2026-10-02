-- Recensioni del venditore: una per ordine.
--
-- Riguardano l'esperienza complessiva (imballo, tempi, descrizione fedele),
-- non il singolo pezzo: nell'usato da collezione ogni articolo e' unico e
-- non tornera' mai in catalogo, quindi una recensione legata al pezzo
-- sarebbe illeggibile per il prossimo cliente.
--
-- order_id e' UNIQUE: chi ha comprato una volta scrive una volta. E' anche
-- la prova che la recensione viene da un acquisto vero — nessuno puo'
-- scrivere senza avere un ordine completato.
--
-- user_id resta NULL per chi ha comprato da ospite: si recensisce con il
-- link ricevuto via email, senza bisogno di un account.
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL UNIQUE REFERENCES orders(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    -- Nome mostrato accanto alla recensione: lo copiamo dall'ordine, cosi'
    -- resta leggibile anche se l'account viene cancellato.
    author_name VARCHAR(255) NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    body TEXT,
    -- Niente va online senza che l'abbia letto l'admin.
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','APPROVED','REJECTED')),
    -- Risposta pubblica del venditore, facoltativa
    reply TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    moderated_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews(status);
CREATE INDEX IF NOT EXISTS idx_reviews_created ON reviews(created_at DESC);
