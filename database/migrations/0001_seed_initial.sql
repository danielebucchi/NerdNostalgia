-- Seed iniziale: admin user + categorie + piattaforme.
-- INSERT idempotenti via INSERT OR IGNORE su slug/username.
--
-- IMPORTANT: La password admin di default e' "changeme" (bcrypt hash sotto).
-- Subito dopo il primo deploy CAMBIALA via:
--   docker exec -it nerdnostalgia-backend python -c "
--     from utils.security import hash_password
--     print(hash_password('la-tua-nuova-password'))"
--   poi UPDATE users SET hashed_password='<hash>' WHERE username='admin';

-- ============================================================
-- Admin user (password: changeme — CAMBIALA SUBITO)
-- ============================================================
INSERT OR IGNORE INTO users (username, email, hashed_password, full_name, role, is_active, is_verified)
VALUES (
    'admin',
    'admin@nerdnostalgia.local',
    '$2b$12$p20hNnFpi2kPTbRmBmQBIuKqQFwOefvpNgW7/9Xh3kJlore2x4MlG',  -- bcrypt('changeme')
    'Administrator',
    'ADMIN',
    1,
    1
);

-- ============================================================
-- Categorie root + sottocategorie
-- ============================================================
INSERT OR IGNORE INTO categories (name, slug, parent_id, display_order) VALUES
    ('Carte', 'carte', NULL, 10),
    ('Videogiochi', 'videogiochi', NULL, 20),
    ('Nerdate', 'nerdate', NULL, 30);

-- Sottocategorie di Carte (id ricavato da slug per portabilita')
INSERT OR IGNORE INTO categories (name, slug, parent_id, display_order)
SELECT 'Pokémon', 'pokemon', id, 10 FROM categories WHERE slug='carte';
INSERT OR IGNORE INTO categories (name, slug, parent_id, display_order)
SELECT 'Magic the Gathering', 'magic-the-gathering', id, 20 FROM categories WHERE slug='carte';
INSERT OR IGNORE INTO categories (name, slug, parent_id, display_order)
SELECT 'Yu-Gi-Oh!', 'yu-gi-oh', id, 30 FROM categories WHERE slug='carte';

-- Sottocategorie di Videogiochi
INSERT OR IGNORE INTO categories (name, slug, parent_id, display_order)
SELECT 'Console', 'console', id, 10 FROM categories WHERE slug='videogiochi';
INSERT OR IGNORE INTO categories (name, slug, parent_id, display_order)
SELECT 'Accessori', 'accessori', id, 20 FROM categories WHERE slug='videogiochi';
INSERT OR IGNORE INTO categories (name, slug, parent_id, display_order)
SELECT 'Giochi', 'giochi', id, 30 FROM categories WHERE slug='videogiochi';

-- Sottocategorie di Nerdate
INSERT OR IGNORE INTO categories (name, slug, parent_id, display_order)
SELECT 'Action Figure', 'action-figure', id, 10 FROM categories WHERE slug='nerdate';
INSERT OR IGNORE INTO categories (name, slug, parent_id, display_order)
SELECT 'Funko Pop', 'funko-pop', id, 20 FROM categories WHERE slug='nerdate';
INSERT OR IGNORE INTO categories (name, slug, parent_id, display_order)
SELECT 'Modellini', 'modellini', id, 30 FROM categories WHERE slug='nerdate';
INSERT OR IGNORE INTO categories (name, slug, parent_id, display_order)
SELECT 'Peluche', 'peluche', id, 40 FROM categories WHERE slug='nerdate';
INSERT OR IGNORE INTO categories (name, slug, parent_id, display_order)
SELECT 'Gadget', 'gadget', id, 50 FROM categories WHERE slug='nerdate';

-- ============================================================
-- Piattaforme (sia vendita che acquisto - unificate)
-- ============================================================
INSERT OR IGNORE INTO platforms (name, slug, icon, display_order, is_active) VALUES
    ('Vinted',     'vinted',     '🛍', 10, 1),
    ('eBay',       'ebay',       '🅔', 20, 1),
    ('mercato',    'mercato',    '🏪', 30, 1),
    ('Subito',     'subito',     '📱', 40, 1),
    ('Wallapop',   'wallapop',   '💬', 50, 1),
    ('CardTrader', 'cardtrader', '🎴', 60, 1),
    ('Privato',    'privato',    '👤', 70, 1),
    ('Regalo',     'regalo',     '🎁', 80, 1),
    ('Altro',      'altro',      '…', 90, 1);
