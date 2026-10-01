-- Assicurazione della spedizione, scelta dal compratore.
--
-- Di default e' attiva dai 50 € in su, ma si puo' cambiare nei due sensi:
-- assicurare un ordine piccolo o rinunciare su uno grande. Salviamo la scelta
-- e quanto e' costata, cosi' l'ordine resta leggibile anche se domani
-- cambiamo le tariffe.
ALTER TABLE orders ADD COLUMN insured BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE orders ADD COLUMN insurance_fee NUMERIC(10,2) NOT NULL DEFAULT 0;
