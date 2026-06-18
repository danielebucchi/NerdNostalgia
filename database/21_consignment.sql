-- Tabella consignment_sales: vendite in contovendita (per conto terzi).
-- L'utente vende un oggetto di un'altra persona (committente), trattiene
-- una commissione e deve girare il resto al committente.
-- PostgreSQL. Idempotente.

CREATE TABLE IF NOT EXISTS consignment_sales (
    id SERIAL PRIMARY KEY,
    sale_date DATE NOT NULL,
    item VARCHAR(255) NOT NULL,
    consignor VARCHAR(100) NOT NULL,
    sale_price DECIMAL(10, 2) NOT NULL,
    commission_pct DECIMAL(5, 2),
    commission_amount DECIMAL(10, 2),
    fee_amount DECIMAL(10, 2),
    shipping_cost DECIMAL(10, 2),
    sold_platform VARCHAR(50),
    sold_by VARCHAR(20),
    buyer VARCHAR(100),
    paid_out BOOLEAN NOT NULL DEFAULT FALSE,
    payout_date DATE,
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_consignment_sale_date ON consignment_sales(sale_date DESC);
CREATE INDEX IF NOT EXISTS idx_consignment_consignor ON consignment_sales(consignor);
CREATE INDEX IF NOT EXISTS idx_consignment_paid_out ON consignment_sales(paid_out);

DROP TRIGGER IF EXISTS update_consignment_sales_updated_at ON consignment_sales;
CREATE TRIGGER update_consignment_sales_updated_at
    BEFORE UPDATE ON consignment_sales
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE consignment_sales IS 'Vendite in contovendita: io vendo, tengo commissione, giro il resto al committente.';
COMMENT ON COLUMN consignment_sales.consignor IS 'Nome del committente (persona che mi ha dato la cosa da vendere)';
COMMENT ON COLUMN consignment_sales.commission_pct IS 'Percentuale che tengo io (es. 10.00 = 10%). Override possibile via commission_amount.';
COMMENT ON COLUMN consignment_sales.commission_amount IS 'Importo €. Se NULL, calcolato come sale_price * commission_pct / 100.';
COMMENT ON COLUMN consignment_sales.paid_out IS 'TRUE quando ho gia'' girato il dovuto al committente.';
