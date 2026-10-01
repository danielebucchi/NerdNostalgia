-- Consegna in locker InPost.
--
-- Da qui si spedisce solo a locker: la destinazione non e' piu' l'indirizzo di
-- casa del compratore ma il punto di ritiro che sceglie sulla mappa. I campi
-- ship_* continuano a contenere l'indirizzo di destinazione (quello del
-- locker), cosi' l'etichetta di spedizione si costruisce come prima; qui
-- teniamo l'identita' del punto, che serve al corriere e all'assistenza.
ALTER TABLE orders ADD COLUMN inpost_point_id VARCHAR(64);
ALTER TABLE orders ADD COLUMN inpost_point_name VARCHAR(255);
