-- Tabella categories gerarchica (categoria/sottocategoria) e migrazione delle
-- colonne `category` testuali esistenti a foreign key.
-- Database: PostgreSQL
--
-- Idempotente: puo' essere rieseguita senza distruggere dati. Mappa best-effort
-- gli slug testuali storici alle nuove categorie.

-- ---------------------------------------------------------------------------
-- 1) Tabella categories
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(120) NOT NULL UNIQUE,
    parent_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_categories_slug ON categories(slug);

DROP TRIGGER IF EXISTS update_categories_updated_at ON categories;
CREATE TRIGGER update_categories_updated_at
    BEFORE UPDATE ON categories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE categories IS 'Categorie e sottocategorie (parent_id NULL = top level)';
COMMENT ON COLUMN categories.parent_id IS 'NULL = categoria top-level, altrimenti FK a sottocategoria';

-- ---------------------------------------------------------------------------
-- 2) Seed top level + sottocategorie
-- ---------------------------------------------------------------------------
INSERT INTO categories (name, slug, parent_id, display_order) VALUES
    ('Carte',       'carte',       NULL, 10),
    ('Videogiochi', 'videogiochi', NULL, 20),
    ('Nerdate',     'nerdate',     NULL, 30)
ON CONFLICT (slug) DO NOTHING;

INSERT INTO categories (name, slug, parent_id, display_order)
SELECT v.name, v.slug, p.id, v.dord
FROM (VALUES
    -- Carte
    ('Pokémon',             'pokemon',             'carte',       10),
    ('Magic the Gathering', 'magic-the-gathering', 'carte',       20),
    ('Yu-Gi-Oh!',           'yu-gi-oh',            'carte',       30),
    ('Dragon Ball',         'dragon-ball',         'carte',       40),
    ('One Piece',           'one-piece',           'carte',       50),
    -- Videogiochi
    ('Console',             'console',             'videogiochi', 10),
    ('Accessori',           'accessori',           'videogiochi', 20),
    ('Giochi',              'giochi',              'videogiochi', 30),
    -- Nerdate
    ('Action Figure',       'action-figure',       'nerdate',     10),
    ('Funko Pop',           'funko-pop',           'nerdate',     20),
    ('Modellini',           'modellini',           'nerdate',     30),
    ('Peluche',             'peluche',             'nerdate',     40),
    ('Gadget',              'gadget',              'nerdate',     50)
) AS v(name, slug, parent_slug, dord)
JOIN categories p ON p.slug = v.parent_slug
ON CONFLICT (slug) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 3) articles: category_id FK + backfill dai vecchi slug + drop colonna
-- ---------------------------------------------------------------------------
ALTER TABLE articles
    ADD COLUMN IF NOT EXISTS category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_articles_category_id ON articles(category_id);

-- Best-effort mapping dei vecchi slug testuali alle nuove categorie
UPDATE articles a SET category_id = c.id
FROM categories c
WHERE a.category_id IS NULL AND a.category IS NOT NULL AND (
    (a.category = 'pokemon-cards' AND c.slug = 'pokemon') OR
    (a.category = 'videogames'    AND c.slug = 'videogiochi') OR
    (a.category = 'funko-pop'     AND c.slug = 'funko-pop')
);

DROP INDEX IF EXISTS idx_articles_category;
ALTER TABLE articles DROP COLUMN IF EXISTS category;

-- ---------------------------------------------------------------------------
-- 4) wanted_items: stessa migrazione
-- ---------------------------------------------------------------------------
ALTER TABLE wanted_items
    ADD COLUMN IF NOT EXISTS category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_wanted_category_id ON wanted_items(category_id);

UPDATE wanted_items w SET category_id = c.id
FROM categories c
WHERE w.category_id IS NULL AND w.category IS NOT NULL AND (
    (w.category = 'pokemon-cards' AND c.slug = 'pokemon') OR
    (w.category = 'videogames'    AND c.slug = 'videogiochi') OR
    (w.category = 'funko-pop'     AND c.slug = 'funko-pop')
);

DROP INDEX IF EXISTS idx_wanted_category;
ALTER TABLE wanted_items DROP COLUMN IF EXISTS category;

-- ---------------------------------------------------------------------------
-- 5) marketplace_fees: category_id + reseed pulito
-- ---------------------------------------------------------------------------
ALTER TABLE marketplace_fees
    ADD COLUMN IF NOT EXISTS category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE;

DROP INDEX IF EXISTS idx_marketplace_fees_lookup;
ALTER TABLE marketplace_fees DROP COLUMN IF EXISTS category;
CREATE INDEX IF NOT EXISTS idx_marketplace_fees_lookup
    ON marketplace_fees(marketplace, category_id);

-- Reseed: rimuove tutti i vecchi markup (avevano category testuale non mappabile
-- in modo affidabile) e ricarica i preset di base sulle nuove categorie.
DELETE FROM marketplace_fees;

INSERT INTO marketplace_fees (marketplace, category_id, markup_percent, note) VALUES
    ('ebay',   NULL, 11.00, 'default'),
    ('vinted', NULL,  0.00, 'fee a carico buyer'),
    ('vinted', NULL,  5.00, 'cuscinetto');

-- eBay: markup specifici per top-level
INSERT INTO marketplace_fees (marketplace, category_id, markup_percent, note)
SELECT 'ebay', c.id, m.markup, m.note
FROM (VALUES
    ('carte',       12.00, 'final value fee collezionismo'),
    ('videogiochi', 10.00, 'commissione standard videogame'),
    ('nerdate',     12.00, 'commissione collezionismo')
) AS m(slug, markup, note)
JOIN categories c ON c.slug = m.slug AND c.parent_id IS NULL;
