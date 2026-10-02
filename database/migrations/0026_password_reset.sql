-- Recupero password: token monouso con scadenza.
--
-- In tabella finisce l'HASH del token, non il token: chi riesce a leggere
-- il database non deve poter entrare in tutti gli account. Il valore in
-- chiaro esiste solo dentro il link mandato per email.
--
-- Due colonne sugli utenti invece di una tabella a parte: di richiesta
-- valida ne esiste una sola per volta, e chiederne una nuova deve
-- invalidare la precedente — con righe separate servirebbe ricordarsi di
-- cancellarle, qui si sovrascrive e basta.
ALTER TABLE users ADD COLUMN reset_token_hash VARCHAR(64);
ALTER TABLE users ADD COLUMN reset_token_expires_at TIMESTAMP;
