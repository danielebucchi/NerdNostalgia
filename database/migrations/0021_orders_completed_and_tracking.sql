-- Stato COMPLETATO + codice di tracciamento.
--
-- Il flusso diventa:  PAGATO → (inserisci il tracking) → SPEDITO → COMPLETATO
--
-- Perche' una ricostruzione della tabella e non un semplice ALTER: lo stato
-- ha un vincolo CHECK con l'elenco dei valori ammessi, e SQLite non permette
-- di modificarlo. L'unica via e' ricreare la tabella.
--
-- E' un'operazione delicata su dati veri, quindi:
--   * tutto dentro una transazione (SQLite ha DDL transazionale: se qualcosa
--     va storto si annulla tutto e la tabella vecchia resta intatta);
--   * colonne elencate una per una, mai SELECT *, cosi' un disallineamento
--     di ordine non travasa dati nella colonna sbagliata;
--   * foreign_keys spente durante lo scambio, altrimenti il DROP della
--     vecchia tabella farebbe scattare le CASCADE su order_items.
PRAGMA foreign_keys=OFF;

BEGIN;

CREATE TABLE orders_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_name VARCHAR(255) NOT NULL,
    buyer_email VARCHAR(255) NOT NULL,
    buyer_phone VARCHAR(50),
    ship_street VARCHAR(255) NOT NULL,
    ship_city VARCHAR(120) NOT NULL,
    ship_postal_code VARCHAR(20) NOT NULL,
    ship_province VARCHAR(120),
    ship_country VARCHAR(80) NOT NULL DEFAULT 'Italia',
    subtotal NUMERIC(10,2) NOT NULL,
    shipping_total NUMERIC(10,2) NOT NULL,
    grand_total NUMERIC(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    notes TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','PAID','SHIPPED','COMPLETED','CANCELLED')),
    paid_at TIMESTAMP,
    shipped_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    admin_notes TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    hand_exchange BOOLEAN NOT NULL DEFAULT 0,
    stripe_session_id VARCHAR(120),
    stripe_payment_intent VARCHAR(120),
    public_token VARCHAR(64),
    paypal_order_id VARCHAR(64),
    paypal_capture_id VARCHAR(64),
    inpost_point_id VARCHAR(64),
    inpost_point_name VARCHAR(255),
    insured BOOLEAN NOT NULL DEFAULT 0,
    insurance_fee NUMERIC(10,2) NOT NULL DEFAULT 0,
    -- Nuove: senza tracking non si puo' marcare spedito
    tracking_carrier VARCHAR(80),
    tracking_code VARCHAR(120),
    completed_at TIMESTAMP
);

INSERT INTO orders_new (
    id, buyer_name, buyer_email, buyer_phone,
    ship_street, ship_city, ship_postal_code, ship_province, ship_country,
    subtotal, shipping_total, grand_total, currency, notes, status,
    paid_at, shipped_at, cancelled_at, admin_notes, ip_address,
    created_at, updated_at, hand_exchange,
    stripe_session_id, stripe_payment_intent, public_token,
    paypal_order_id, paypal_capture_id,
    inpost_point_id, inpost_point_name, insured, insurance_fee
)
SELECT
    id, buyer_name, buyer_email, buyer_phone,
    ship_street, ship_city, ship_postal_code, ship_province, ship_country,
    subtotal, shipping_total, grand_total, currency, notes, status,
    paid_at, shipped_at, cancelled_at, admin_notes, ip_address,
    created_at, updated_at, hand_exchange,
    stripe_session_id, stripe_payment_intent, public_token,
    paypal_order_id, paypal_capture_id,
    inpost_point_id, inpost_point_name, insured, insurance_fee
FROM orders;

DROP TABLE orders;
ALTER TABLE orders_new RENAME TO orders;

CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_email ON orders(buyer_email);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);

COMMIT;

PRAGMA foreign_keys=ON;
