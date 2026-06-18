-- Aggiunge kind a misc_sales per distinguere vendite esterne generiche
-- da vendite di creazioni handmade.
-- Aggiunge anche related_to_creations alle expenses (analogo a related_to_cards).
-- PostgreSQL. Idempotente.

ALTER TABLE misc_sales ADD COLUMN IF NOT EXISTS kind VARCHAR(20) NOT NULL DEFAULT 'external';
ALTER TABLE misc_sales ADD COLUMN IF NOT EXISTS material_cost DECIMAL(10, 2);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'misc_sales_kind_check'
    ) THEN
        ALTER TABLE misc_sales
            ADD CONSTRAINT misc_sales_kind_check
            CHECK (kind IN ('external', 'creation'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_misc_sales_kind ON misc_sales(kind);

COMMENT ON COLUMN misc_sales.kind IS 'external = vendita esterna generica, creation = creazione handmade';
COMMENT ON COLUMN misc_sales.material_cost IS 'Solo per creation: costo materiali (usato per calcolo profitto)';

ALTER TABLE expenses ADD COLUMN IF NOT EXISTS related_to_creations BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_expenses_related_creations ON expenses(related_to_creations);

COMMENT ON COLUMN expenses.related_to_creations IS
    'Se TRUE, questa spesa va sottratta anche dal profitto netto delle creazioni.';
