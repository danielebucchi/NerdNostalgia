-- Link per seguire la spedizione.
--
-- Il codice da solo obbliga il compratore a cercare il sito del corriere e
-- incollarcelo dentro. Il link lo porta direttamente alla pagina del suo
-- pacco, ed e' quello che finisce nell'email di spedizione.
ALTER TABLE orders ADD COLUMN tracking_url VARCHAR(500);
