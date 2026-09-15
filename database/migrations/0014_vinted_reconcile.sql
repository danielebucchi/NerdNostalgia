-- 0014_vinted_reconcile
-- Contatore degli articoli archiviati dalla riconciliazione: item spariti
-- da Vinted (404 confermato) che vengono tolti dal catalogo pubblico.
ALTER TABLE vinted_sync_logs ADD COLUMN items_archived INTEGER NOT NULL DEFAULT 0;
