-- Estensione articles + tabelle ausiliarie per replicare l'inventario del
-- foglio "Cate 2026":
--   * Flipping Inventario / Carte Pokemon Inventario → colonne extra in articles
--   * Spese carte                                    → tabella card_purchases
--   * Vendite                                        → tabella misc_sales
-- Idempotente: puo' essere rieseguita senza danni.

-- ---------------------------------------------------------------------------
-- 1) articles: campi inventory (costo, piattaforma acquisto, fee, ecc.)
-- ---------------------------------------------------------------------------
ALTER TABLE articles
    ADD COLUMN IF NOT EXISTS lotto VARCHAR(50),
    ADD COLUMN IF NOT EXISTS purchase_date DATE,
    ADD COLUMN IF NOT EXISTS cost DECIMAL(10, 2),
    ADD COLUMN IF NOT EXISTS purchase_platform VARCHAR(50),
    ADD COLUMN IF NOT EXISTS bought_by VARCHAR(20),
    ADD COLUMN IF NOT EXISTS sold_by VARCHAR(20),
    ADD COLUMN IF NOT EXISTS fee_amount DECIMAL(10, 2),
    ADD COLUMN IF NOT EXISTS shipping_cost DECIMAL(10, 2),
    ADD COLUMN IF NOT EXISTS quantity_sold INTEGER NOT NULL DEFAULT 0,
    -- Campi specifici per carte (Pokemon/Magic/etc)
    ADD COLUMN IF NOT EXISTS card_collection VARCHAR(100),
    ADD COLUMN IF NOT EXISTS card_number VARCHAR(50),
    ADD COLUMN IF NOT EXISTS card_finish VARCHAR(50);

CREATE INDEX IF NOT EXISTS idx_articles_lotto ON articles(lotto);
CREATE INDEX IF NOT EXISTS idx_articles_purchase_date ON articles(purchase_date);
CREATE INDEX IF NOT EXISTS idx_articles_purchase_platform ON articles(purchase_platform);

COMMENT ON COLUMN articles.lotto IS 'Identificativo lotto di acquisto (raggruppa piu articoli comprati insieme)';
COMMENT ON COLUMN articles.cost IS 'Costo unitario di acquisto. NULL = non tracciato';
COMMENT ON COLUMN articles.purchase_platform IS 'Piattaforma di acquisto: Vinted, mercato, Subito, regalo, ecc';
COMMENT ON COLUMN articles.bought_by IS 'Iniziale di chi ha comprato (C, D, ...)';
COMMENT ON COLUMN articles.sold_by IS 'Iniziale di chi ha venduto';
COMMENT ON COLUMN articles.fee_amount IS 'Commissione marketplace effettivamente pagata sulla vendita';
COMMENT ON COLUMN articles.shipping_cost IS 'Costo di spedizione effettivo';
COMMENT ON COLUMN articles.quantity_sold IS 'Quanti pezzi del lotto sono stati venduti';
COMMENT ON COLUMN articles.card_collection IS 'Collezione carta (es. Base Set, Sword & Shield)';
COMMENT ON COLUMN articles.card_number IS 'Numero carta nella collezione (es. 4/102)';
COMMENT ON COLUMN articles.card_finish IS 'Finitura carta: normal, holo, reverse, full art, ...';

-- ---------------------------------------------------------------------------
-- 2) card_purchases: spese carte all'ingrosso (bustine, lotti)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS card_purchases (
    id SERIAL PRIMARY KEY,
    purchase_date DATE,
    item VARCHAR(255) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    note VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_card_purchases_date ON card_purchases(purchase_date DESC);

DROP TRIGGER IF EXISTS update_card_purchases_updated_at ON card_purchases;
CREATE TRIGGER update_card_purchases_updated_at
    BEFORE UPDATE ON card_purchases
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE card_purchases IS
    'Acquisti carte all''ingrosso (bustine, lotti) che non finiscono come articoli singoli';

-- ---------------------------------------------------------------------------
-- 3) misc_sales: vendite varie (vestiti, gadget, robe senza scheda articolo)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS misc_sales (
    id SERIAL PRIMARY KEY,
    sale_date DATE,
    item VARCHAR(255) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    seller VARCHAR(20),
    platform VARCHAR(50),
    paid_by_buyer BOOLEAN NOT NULL DEFAULT TRUE,
    note VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_misc_sales_date ON misc_sales(sale_date DESC);
CREATE INDEX IF NOT EXISTS idx_misc_sales_seller ON misc_sales(seller);

DROP TRIGGER IF EXISTS update_misc_sales_updated_at ON misc_sales;
CREATE TRIGGER update_misc_sales_updated_at
    BEFORE UPDATE ON misc_sales
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE misc_sales IS
    'Vendite generiche su Vinted/Wallapop/mercato di articoli che non hanno scheda nel catalogo (vestiti, libri, oggetti vari)';
COMMENT ON COLUMN misc_sales.paid_by_buyer IS
    'TRUE = pagato dal compratore (importo gia incassato); FALSE = in attesa di pagamento';
