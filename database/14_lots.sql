-- Promozione di 'lotto' (stringa scatter) a entita' Lot di prima classe.
-- Aggiunge anche status enum esplicito + colonna images sugli item.
-- PostgreSQL. Idempotente.

-- ============================================================
-- 1. Tabella lots
-- ============================================================
CREATE TABLE IF NOT EXISTS lots (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    title VARCHAR(200),
    purchase_date DATE,
    purchase_platform VARCHAR(50),
    bought_by VARCHAR(20),
    total_cost DECIMAL(10, 2),
    notes TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT lots_status_check CHECK (status IN ('OPEN','CLOSED','ARCHIVED'))
);

CREATE INDEX IF NOT EXISTS idx_lots_purchase_date ON lots(purchase_date DESC);
CREATE INDEX IF NOT EXISTS idx_lots_status ON lots(status);

DROP TRIGGER IF EXISTS update_lots_updated_at ON lots;
CREATE TRIGGER update_lots_updated_at
    BEFORE UPDATE ON lots
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE lots IS 'Lotto = container di inventory_items con metadati di acquisto comuni';
COMMENT ON COLUMN lots.code IS 'Codice auto-incrementale L0001, L0002, ...';
COMMENT ON COLUMN lots.title IS 'Nome libero del lotto (es. valore originale della vecchia stringa lotto)';

-- ============================================================
-- 2. Colonne nuove su inventory_items
-- ============================================================
ALTER TABLE inventory_items ADD COLUMN IF NOT EXISTS lot_id INTEGER;
ALTER TABLE inventory_items ADD COLUMN IF NOT EXISTS status VARCHAR(20);
ALTER TABLE inventory_items ADD COLUMN IF NOT EXISTS images JSONB NOT NULL DEFAULT '[]'::jsonb;

-- ============================================================
-- 3. Migrazione dati: distinct lotto string -> lots rows
-- ============================================================
DO $migrate$
DECLARE
    next_seq INTEGER;
BEGIN
    -- Skip se gia' migrato (tutti gli item hanno gia' lot_id)
    IF NOT EXISTS (SELECT 1 FROM inventory_items WHERE lot_id IS NULL) THEN
        RAISE NOTICE 'Migrazione lots gia'' eseguita, skip';
        RETURN;
    END IF;

    SELECT COALESCE(MAX(CAST(SUBSTRING(code FROM 2) AS INTEGER)), 0)
        INTO next_seq
        FROM lots
        WHERE code ~ '^L[0-9]+$';

    -- Crea un Lot per ogni stringa lotto distinta non vuota
    WITH distinct_lotti AS (
        SELECT
            lotto,
            MIN(id) AS min_id,
            MIN(purchase_date) AS purchase_date,
            MAX(purchase_platform) AS purchase_platform,
            MAX(bought_by) AS bought_by,
            SUM(COALESCE(cost, 0) * GREATEST(quantity, 1)) AS total_cost
        FROM inventory_items
        WHERE lotto IS NOT NULL AND lotto <> '' AND lot_id IS NULL
        GROUP BY lotto
    ),
    numbered AS (
        SELECT
            lotto,
            ROW_NUMBER() OVER (ORDER BY min_id) AS rn,
            purchase_date,
            purchase_platform,
            bought_by,
            total_cost
        FROM distinct_lotti
    ),
    inserted AS (
        INSERT INTO lots (code, title, purchase_date, purchase_platform, bought_by, total_cost, status)
        SELECT
            'L' || LPAD((next_seq + rn)::text, 4, '0'),
            lotto,
            purchase_date,
            purchase_platform,
            bought_by,
            total_cost,
            'OPEN'
        FROM numbered
        RETURNING id, title
    )
    UPDATE inventory_items i
        SET lot_id = ins.id
        FROM inserted ins
        WHERE i.lotto = ins.title AND i.lot_id IS NULL;

    -- Aggiorna next_seq dopo gli insert
    SELECT COALESCE(MAX(CAST(SUBSTRING(code FROM 2) AS INTEGER)), 0)
        INTO next_seq
        FROM lots
        WHERE code ~ '^L[0-9]+$';

    -- Item orfani (lotto NULL o '') -> ognuno il suo Lot fittizio
    DECLARE
        orphan RECORD;
        new_lot_id INTEGER;
    BEGIN
        FOR orphan IN
            SELECT * FROM inventory_items WHERE lot_id IS NULL ORDER BY id
        LOOP
            next_seq := next_seq + 1;
            INSERT INTO lots (code, title, purchase_date, purchase_platform, bought_by, total_cost, status)
            VALUES (
                'L' || LPAD(next_seq::text, 4, '0'),
                'Singolo: ' || LEFT(orphan.title, 100),
                orphan.purchase_date,
                orphan.purchase_platform,
                orphan.bought_by,
                COALESCE(orphan.cost, 0) * GREATEST(orphan.quantity, 1),
                'OPEN'
            )
            RETURNING id INTO new_lot_id;
            UPDATE inventory_items SET lot_id = new_lot_id WHERE id = orphan.id;
        END LOOP;
    END;
END
$migrate$;

-- ============================================================
-- 4. Backfill status enum
-- ============================================================
UPDATE inventory_items SET status = CASE
    WHEN sold_date IS NOT NULL OR quantity_sold >= quantity THEN 'SOLD'
    WHEN article_id IS NOT NULL AND listed = TRUE  THEN 'LISTED'
    WHEN article_id IS NOT NULL                    THEN 'LINKED'
    ELSE 'DRAFT'
END
WHERE status IS NULL;

-- ============================================================
-- 5. Constraint finali
-- ============================================================
ALTER TABLE inventory_items ALTER COLUMN lot_id SET NOT NULL;
ALTER TABLE inventory_items ALTER COLUMN status SET NOT NULL;
ALTER TABLE inventory_items ALTER COLUMN status SET DEFAULT 'DRAFT';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_inventory_items_lot'
    ) THEN
        ALTER TABLE inventory_items
            ADD CONSTRAINT fk_inventory_items_lot
            FOREIGN KEY (lot_id) REFERENCES lots(id) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'inventory_items_status_check'
    ) THEN
        ALTER TABLE inventory_items
            ADD CONSTRAINT inventory_items_status_check
            CHECK (status IN ('DRAFT','LINKED','LISTED','RESERVED','SOLD','ARCHIVED'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_inventory_lot_id ON inventory_items(lot_id);
CREATE INDEX IF NOT EXISTS idx_inventory_status ON inventory_items(status);

-- ============================================================
-- 6. Drop colonne legacy (ora promosse al Lot)
-- ============================================================
ALTER TABLE inventory_items DROP COLUMN IF EXISTS lotto;
ALTER TABLE inventory_items DROP COLUMN IF EXISTS purchase_date;
ALTER TABLE inventory_items DROP COLUMN IF EXISTS purchase_platform;
ALTER TABLE inventory_items DROP COLUMN IF EXISTS bought_by;
ALTER TABLE inventory_items DROP COLUMN IF EXISTS listed;

DROP INDEX IF EXISTS idx_inventory_lotto;
DROP INDEX IF EXISTS idx_inventory_purchase_date;

COMMENT ON COLUMN inventory_items.lot_id IS 'FK obbligatoria: ogni item appartiene a un Lot';
COMMENT ON COLUMN inventory_items.status IS 'Stato esplicito: DRAFT|LINKED|LISTED|RESERVED|SOLD|ARCHIVED';
COMMENT ON COLUMN inventory_items.images IS 'Foto item (precaricate prima della pubblicazione Article)';
