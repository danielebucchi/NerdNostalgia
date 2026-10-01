-- Prenotazione dell'articolo mentre un ordine e' in attesa di conferma.
--
-- Problema: creato l'ordine, l'articolo restava PUBLISHED e chiunque altro
-- poteva comprarlo. Due persone potevano ordinare lo stesso pezzo unico.
--
-- Perche' una prenotazione e non un nuovo stato 'RESERVED': in SQLite lo
-- stato ha un vincolo CHECK e cambiarlo richiede di ricostruire la tabella
-- articles (rischioso). In piu' cosi' l'annullamento riporta l'articolo
-- esattamente com'era, anche se era in bozza: non dobbiamo ricordarci lo
-- stato precedente.
ALTER TABLE articles ADD COLUMN reserved_order_id INTEGER
    REFERENCES orders(id) ON DELETE SET NULL;
ALTER TABLE articles ADD COLUMN reserved_at TIMESTAMP;
