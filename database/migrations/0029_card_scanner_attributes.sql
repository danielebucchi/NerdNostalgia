-- Scanner carte: reverse, prima edizione, condizione.
-- L'indice ricorda quali attributi CardTrader ammette per ogni carta;
-- lo scan tiene il retro (facoltativo) e l'analisi della carta scelta.
ALTER TABLE card_blueprints ADD COLUMN editable VARCHAR(255);
ALTER TABLE card_scans ADD COLUMN back_image_url VARCHAR(500);
ALTER TABLE card_scans ADD COLUMN features JSON NOT NULL DEFAULT '{}';
