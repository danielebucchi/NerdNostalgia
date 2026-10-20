-- Categoria principale "Giocattoli": Gormiti, Bakugan, Beyblade e gli altri
-- giochi da bambini anni 2000, che non sono action figure da collezione né
-- modellini. Le serie più trattate hanno una sottocategoria; il resto
-- (GoGo's, Crazy Bones, Tamagotchi...) va in "Altri giocattoli".
INSERT OR IGNORE INTO categories (name, slug, parent_id, display_order) VALUES
    ('Giocattoli', 'giocattoli', NULL, 40);

INSERT OR IGNORE INTO categories (name, slug, parent_id, display_order)
SELECT 'Gormiti', 'gormiti', id, 10 FROM categories WHERE slug='giocattoli';
INSERT OR IGNORE INTO categories (name, slug, parent_id, display_order)
SELECT 'Bakugan', 'bakugan', id, 20 FROM categories WHERE slug='giocattoli';
INSERT OR IGNORE INTO categories (name, slug, parent_id, display_order)
SELECT 'Beyblade', 'beyblade', id, 30 FROM categories WHERE slug='giocattoli';
INSERT OR IGNORE INTO categories (name, slug, parent_id, display_order)
SELECT 'Altri giocattoli', 'altri-giocattoli', id, 90 FROM categories WHERE slug='giocattoli';
