-- Tabelle orders + order_items per gli ordini di acquisto.
-- Vedi commento esteso in schema.sql.

CREATE TABLE IF NOT EXISTS orders (
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
        CHECK (status IN ('PENDING','PAID','SHIPPED','CANCELLED')),
    paid_at TIMESTAMP,
    shipped_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    admin_notes TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_email ON orders(buyer_email);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
    title_snapshot VARCHAR(255) NOT NULL,
    price_snapshot NUMERIC(10,2) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_article ON order_items(article_id);
