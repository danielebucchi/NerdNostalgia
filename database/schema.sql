-- NerdNostalgia — Schema SQLite consolidato.
-- Sostituisce le migrazioni Postgres in _legacy_postgres/.
-- updated_at e' gestito dal layer SQLAlchemy (onupdate=datetime.utcnow),
-- niente trigger DB. CHECK al posto di ENUM. JSONB diventa JSON (TEXT).

PRAGMA foreign_keys = ON;

-- ============================================================
-- users
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(20) NOT NULL DEFAULT 'USER'
        CHECK (role IN ('ADMIN','USER','GUEST')),
    is_active INTEGER NOT NULL DEFAULT 1,
    is_verified INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- ============================================================
-- categories
-- ============================================================
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(120) NOT NULL UNIQUE,
    parent_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_categories_slug ON categories(slug);

-- ============================================================
-- articles
-- ============================================================
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    price NUMERIC(10,2) NOT NULL,
    -- Costo spedizione mostrato al cliente (somma a price nel link PayPal).
    -- Diverso da shipping_cost piu' sotto, che e' la spesa sostenuta per
    -- tracking interno profit/loss (es. potrebbe essere applicato ricarico).
    -- Default 5 EUR: copre piego di libri raccomandato per la maggior
    -- parte degli articoli, override manuale per cose voluminose.
    shipping_price NUMERIC(10,2) DEFAULT 5.00,
    currency VARCHAR(3) DEFAULT 'EUR',
    condition VARCHAR(20) NOT NULL DEFAULT 'USED'
        CHECK (condition IN ('NEW','USED','REFURBISHED','FOR_PARTS')),
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT','PUBLISHED','SOLD','ARCHIVED')),
    quantity INTEGER NOT NULL DEFAULT 1,
    sku VARCHAR(100) UNIQUE,
    brand VARCHAR(100),
    model VARCHAR(100),
    weight_kg NUMERIC(8,2),
    dimensions_cm VARCHAR(50),
    images JSON DEFAULT '[]',
    article_metadata JSON DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP,
    sold_at TIMESTAMP,
    display_order INTEGER NOT NULL DEFAULT 0,
    vinted_status VARCHAR(20) NOT NULL DEFAULT 'NOT_LISTED'
        CHECK (vinted_status IN ('NOT_LISTED','LISTED','SOLD')),
    vinted_url VARCHAR(500),
    vinted_synced_at TIMESTAMP,
    ebay_status VARCHAR(20) NOT NULL DEFAULT 'NOT_LISTED'
        CHECK (ebay_status IN ('NOT_LISTED','LISTED','SOLD')),
    ebay_url VARCHAR(500),
    ebay_synced_at TIMESTAMP,
    vinted_price NUMERIC(10,2),
    ebay_price NUMERIC(10,2),
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    lotto VARCHAR(50),
    purchase_date DATE,
    cost NUMERIC(10,2),
    purchase_platform VARCHAR(50),
    bought_by VARCHAR(20),
    sold_by VARCHAR(20),
    fee_amount NUMERIC(10,2),
    shipping_cost NUMERIC(10,2),
    quantity_sold INTEGER NOT NULL DEFAULT 0,
    card_collection VARCHAR(100),
    card_number VARCHAR(50),
    card_finish VARCHAR(50),
    card_condition VARCHAR(30),
    card_language VARCHAR(5),
    card_reverse INTEGER NOT NULL DEFAULT 0,
    card_first_edition INTEGER NOT NULL DEFAULT 0,
    vinted_item_id BIGINT,
    cardtrader_blueprint_id BIGINT,
    cardtrader_product_id BIGINT,
    cardtrader_synced_at TIMESTAMP,
    ebay_sku VARCHAR(50),
    ebay_offer_id VARCHAR(30),
    ebay_listing_id VARCHAR(30)
);
CREATE INDEX IF NOT EXISTS idx_articles_user_id ON articles(user_id);
CREATE INDEX IF NOT EXISTS idx_articles_category_id ON articles(category_id);
CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
CREATE INDEX IF NOT EXISTS idx_articles_condition ON articles(condition);
CREATE INDEX IF NOT EXISTS idx_articles_price ON articles(price);
CREATE INDEX IF NOT EXISTS idx_articles_created_at ON articles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_display_order ON articles(display_order, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_sku ON articles(sku);
CREATE INDEX IF NOT EXISTS idx_articles_lotto ON articles(lotto);
CREATE INDEX IF NOT EXISTS idx_articles_purchase_date ON articles(purchase_date);
CREATE INDEX IF NOT EXISTS idx_articles_purchase_platform ON articles(purchase_platform);
CREATE INDEX IF NOT EXISTS idx_articles_vinted_status ON articles(vinted_status);
CREATE INDEX IF NOT EXISTS idx_articles_ebay_status ON articles(ebay_status);
CREATE UNIQUE INDEX IF NOT EXISTS uq_articles_vinted_item ON articles(vinted_item_id) WHERE vinted_item_id IS NOT NULL;

-- ============================================================
-- inquiries
-- ============================================================
CREATE TABLE IF NOT EXISTS inquiries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    subject VARCHAR(255),
    message TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'NEW'
        CHECK (status IN ('NEW','READ','REPLIED','CLOSED')),
    ip_address VARCHAR(45),
    admin_notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    replied_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_inquiries_article_id ON inquiries(article_id);
CREATE INDEX IF NOT EXISTS idx_inquiries_email ON inquiries(email);
CREATE INDEX IF NOT EXISTS idx_inquiries_status ON inquiries(status);
CREATE INDEX IF NOT EXISTS idx_inquiries_created_at ON inquiries(created_at DESC);

-- ============================================================
-- orders + order_items: ordini di acquisto dal sito.
-- Il pagamento e' fuori sistema (paypal.me), quindi un Order parte come
-- PENDING quando il compratore submit-ta il form e diventa PAID solo
-- quando l'admin lo conferma manualmente da /admin/ordini.
-- ============================================================
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Dati compratore
    buyer_name VARCHAR(255) NOT NULL,
    buyer_email VARCHAR(255) NOT NULL,
    buyer_phone VARCHAR(50),
    -- Indirizzo spedizione (campi separati per filtrare / esportare)
    ship_street VARCHAR(255) NOT NULL,
    ship_city VARCHAR(120) NOT NULL,
    ship_postal_code VARCHAR(20) NOT NULL,
    ship_province VARCHAR(120),
    ship_country VARCHAR(80) NOT NULL DEFAULT 'Italia',
    -- Importi (snapshot al momento del checkout, indipendenti da future
    -- modifiche dei prezzi articolo)
    subtotal NUMERIC(10,2) NOT NULL,
    shipping_total NUMERIC(10,2) NOT NULL,
    grand_total NUMERIC(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    notes TEXT,
    -- Scambio a mano: compratore residente in LI/PI, niente spedizione.
    -- Validato lato API che il CAP cominci con 56 (Pisa) o 57 (Livorno).
    hand_exchange BOOLEAN NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','PAID','SHIPPED','CANCELLED')),
    paid_at TIMESTAMP,
    shipped_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    admin_notes TEXT,
    -- Tracking IP per rate-limit / antifrode
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
    -- SET NULL: se l'articolo viene cancellato non perdiamo lo storico ordine.
    article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
    -- Snapshot del titolo + prezzo al momento dell'ordine (immutabile).
    title_snapshot VARCHAR(255) NOT NULL,
    price_snapshot NUMERIC(10,2) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_article ON order_items(article_id);

-- ============================================================
-- wanted_items
-- ============================================================
CREATE TABLE IF NOT EXISTS wanted_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    brand VARCHAR(100),
    model VARCHAR(100),
    preferred_condition VARCHAR(20)
        CHECK (preferred_condition IS NULL OR preferred_condition IN ('NEW','USED','REFURBISHED','FOR_PARTS')),
    max_price NUMERIC(10,2),
    currency VARCHAR(3) DEFAULT 'EUR',
    notes TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','FULFILLED','CLOSED')),
    priority INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fulfilled_at TIMESTAMP,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_wanted_status ON wanted_items(status);
CREATE INDEX IF NOT EXISTS idx_wanted_priority ON wanted_items(priority DESC);
CREATE INDEX IF NOT EXISTS idx_wanted_created_at ON wanted_items(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_wanted_category_id ON wanted_items(category_id);

-- ============================================================
-- card_purchases (spese carte legacy)
-- ============================================================
CREATE TABLE IF NOT EXISTS card_purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_date DATE,
    item VARCHAR(255) NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    note VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_card_purchases_date ON card_purchases(purchase_date DESC);

-- ============================================================
-- misc_sales (vendite esterne + creazioni)
-- ============================================================
CREATE TABLE IF NOT EXISTS misc_sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_date DATE,
    item VARCHAR(255) NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    seller VARCHAR(20),
    platform VARCHAR(50),
    paid_by_buyer INTEGER NOT NULL DEFAULT 1,
    note VARCHAR(255),
    kind VARCHAR(20) NOT NULL DEFAULT 'external'
        CHECK (kind IN ('external','creation')),
    material_cost NUMERIC(10,2),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_misc_sales_date ON misc_sales(sale_date DESC);
CREATE INDEX IF NOT EXISTS idx_misc_sales_seller ON misc_sales(seller);
CREATE INDEX IF NOT EXISTS idx_misc_sales_kind ON misc_sales(kind);

-- ============================================================
-- marketplace_fees
-- ============================================================
CREATE TABLE IF NOT EXISTS marketplace_fees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    marketplace VARCHAR(50) NOT NULL,
    markup_percent NUMERIC(5,2) NOT NULL,
    note VARCHAR(255),
    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_marketplace_fees_lookup ON marketplace_fees(marketplace, category_id);

-- ============================================================
-- vinted_settings + vinted_sync_logs
-- ============================================================
CREATE TABLE IF NOT EXISTS vinted_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vinted_user_id BIGINT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    sync_hour INTEGER NOT NULL DEFAULT 4,
    last_run_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vinted_sync_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    triggered_by VARCHAR(20) NOT NULL DEFAULT 'cron',
    items_fetched INTEGER NOT NULL DEFAULT 0,
    items_imported INTEGER NOT NULL DEFAULT 0,
    items_updated INTEGER NOT NULL DEFAULT 0,
    items_skipped INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_vinted_logs_started ON vinted_sync_logs(started_at DESC);

-- ============================================================
-- lots
-- ============================================================
CREATE TABLE IF NOT EXISTS lots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    title VARCHAR(200),
    purchase_date DATE,
    purchase_platform VARCHAR(50),
    bought_by VARCHAR(20),
    total_cost NUMERIC(10,2),
    notes TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN','CLOSED','ARCHIVED')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_lots_status ON lots(status);
CREATE INDEX IF NOT EXISTS idx_lots_purchase_date ON lots(purchase_date DESC);

-- ============================================================
-- inventory_items
-- ============================================================
CREATE TABLE IF NOT EXISTS inventory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    cost NUMERIC(10,2),
    list_price NUMERIC(10,2),
    sold_date DATE,
    sold_by VARCHAR(20),
    sold_platform VARCHAR(50),
    sale_price NUMERIC(10,2),
    fee_amount NUMERIC(10,2),
    shipping_cost NUMERIC(10,2),
    quantity INTEGER NOT NULL DEFAULT 1,
    quantity_sold INTEGER NOT NULL DEFAULT 0,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    card_collection VARCHAR(100),
    card_number VARCHAR(50),
    card_finish VARCHAR(50),
    card_condition VARCHAR(30),
    card_language VARCHAR(5),
    card_reverse INTEGER NOT NULL DEFAULT 0,
    card_first_edition INTEGER NOT NULL DEFAULT 0,
    article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
    vinted_item_id BIGINT,
    notes TEXT,
    lot_id INTEGER NOT NULL REFERENCES lots(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT','LINKED','LISTED','RESERVED','SOLD','ARCHIVED')),
    images JSON NOT NULL DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_inventory_lot_id ON inventory_items(lot_id);
CREATE INDEX IF NOT EXISTS idx_inventory_article ON inventory_items(article_id);
CREATE INDEX IF NOT EXISTS idx_inventory_category ON inventory_items(category_id);
CREATE INDEX IF NOT EXISTS idx_inventory_status ON inventory_items(status);
CREATE INDEX IF NOT EXISTS idx_inventory_sold_date ON inventory_items(sold_date DESC);

-- ============================================================
-- personal_cards
-- ============================================================
CREATE TABLE IF NOT EXISTS personal_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    collection VARCHAR(100),
    card_number VARCHAR(50),
    finish VARCHAR(50),
    language VARCHAR(20) DEFAULT 'IT',
    condition VARCHAR(20),
    grading VARCHAR(20),
    owned_by VARCHAR(20),
    quantity INTEGER NOT NULL DEFAULT 1,
    purchase_date DATE,
    purchase_cost NUMERIC(10,2),
    purchase_source VARCHAR(50),
    bulk_source VARCHAR(100),
    estimated_value NUMERIC(10,2),
    estimated_value_updated_at DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'IN_STOCK'
        CHECK (status IN ('IN_STOCK','RESERVED','SOLD','ARCHIVED')),
    sold_date DATE,
    sold_by VARCHAR(20),
    sold_platform VARCHAR(50),
    sale_price NUMERIC(10,2),
    fee_amount NUMERIC(10,2),
    shipping_cost NUMERIC(10,2),
    images JSON NOT NULL DEFAULT '[]',
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_personal_cards_collection ON personal_cards(collection);
CREATE INDEX IF NOT EXISTS idx_personal_cards_owned_by ON personal_cards(owned_by);
CREATE INDEX IF NOT EXISTS idx_personal_cards_purchase_date ON personal_cards(purchase_date DESC);
CREATE INDEX IF NOT EXISTS idx_personal_cards_status ON personal_cards(status);
CREATE INDEX IF NOT EXISTS idx_personal_cards_sold_date ON personal_cards(sold_date DESC);

-- ============================================================
-- expenses
-- ============================================================
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spend_date DATE NOT NULL,
    item VARCHAR(255) NOT NULL,
    category VARCHAR(50),
    amount NUMERIC(10,2) NOT NULL,
    paid_by VARCHAR(20),
    related_to_cards INTEGER NOT NULL DEFAULT 0,
    related_to_creations INTEGER NOT NULL DEFAULT 0,
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_expenses_spend_date ON expenses(spend_date DESC);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);
CREATE INDEX IF NOT EXISTS idx_expenses_related_cards ON expenses(related_to_cards);
CREATE INDEX IF NOT EXISTS idx_expenses_related_creations ON expenses(related_to_creations);

-- ============================================================
-- platforms
-- ============================================================
CREATE TABLE IF NOT EXISTS platforms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL,
    slug VARCHAR(50) NOT NULL UNIQUE,
    icon VARCHAR(10),
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_platforms_active ON platforms(is_active);
CREATE INDEX IF NOT EXISTS idx_platforms_order ON platforms(display_order);
CREATE INDEX IF NOT EXISTS idx_platforms_slug ON platforms(slug);

-- ============================================================
-- consignment_sales
-- ============================================================
CREATE TABLE IF NOT EXISTS consignment_sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_date DATE NOT NULL,
    item VARCHAR(255) NOT NULL,
    consignor VARCHAR(100) NOT NULL,
    sale_price NUMERIC(10,2) NOT NULL,
    commission_pct NUMERIC(5,2),
    commission_amount NUMERIC(10,2),
    fee_amount NUMERIC(10,2),
    shipping_cost NUMERIC(10,2),
    sold_platform VARCHAR(50),
    sold_by VARCHAR(20),
    buyer VARCHAR(100),
    paid_out INTEGER NOT NULL DEFAULT 0,
    payout_date DATE,
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_consignment_sale_date ON consignment_sales(sale_date DESC);
CREATE INDEX IF NOT EXISTS idx_consignment_consignor ON consignment_sales(consignor);
CREATE INDEX IF NOT EXISTS idx_consignment_paid_out ON consignment_sales(paid_out);

-- ============================================================
-- settings (config runtime chiave/valore, vedi migrazione 0008)
-- ============================================================
CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- category_alerts (avvisi nuovi arrivi, vedi migrazione 0009)
-- ============================================================
CREATE TABLE IF NOT EXISTS category_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) NOT NULL,
    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (email, category_id)
);
CREATE INDEX IF NOT EXISTS idx_category_alerts_category
    ON category_alerts(category_id);
