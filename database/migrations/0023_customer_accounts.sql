-- Account cliente: consenso promozionale e ordini legati al profilo.
--
-- Gli account dei clienti riusano la tabella users con ruolo USER: stesso
-- login, stesso token, cambia solo cosa gli si lascia fare. Non serve una
-- tabella a parte, e l'admin resta l'unico con ruolo ADMIN.
--
-- Consenso promozionale: NON e' incluso nella registrazione. Il GDPR vuole
-- che sia libero e separato, quindi e' una spunta a parte, di default
-- spenta, e teniamo traccia di QUANDO e' stato dato (o revocato): senza data
-- il consenso non e' dimostrabile.
ALTER TABLE users ADD COLUMN marketing_consent BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN marketing_consent_at TIMESTAMP;
-- Token opaco per il link "disiscriviti" nelle email promozionali: deve
-- funzionare senza login, perche' chi vuole uscire non deve prima entrare.
ALTER TABLE users ADD COLUMN unsubscribe_token VARCHAR(64);

-- Ordine collegato al profilo. Resta NULL per gli acquisti da ospite: si
-- compra anche senza account, e l'ordine si riaggancia dopo se chi l'ha
-- fatto si registra con la stessa email.
ALTER TABLE orders ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
