-- Tabella expenses: foglio "Spese" generiche.
-- Diversa da card_purchases (foglio "Spese carte") che resta separata.
-- PostgreSQL. Idempotente.

CREATE TABLE IF NOT EXISTS expenses (
    id SERIAL PRIMARY KEY,
    spend_date DATE NOT NULL,
    item VARCHAR(255) NOT NULL,
    category VARCHAR(50),
    amount DECIMAL(10, 2) NOT NULL,
    paid_by VARCHAR(20),
    related_to_cards BOOLEAN NOT NULL DEFAULT FALSE,
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_expenses_spend_date ON expenses(spend_date DESC);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);
CREATE INDEX IF NOT EXISTS idx_expenses_related_cards ON expenses(related_to_cards);

DROP TRIGGER IF EXISTS update_expenses_updated_at ON expenses;
CREATE TRIGGER update_expenses_updated_at
    BEFORE UPDATE ON expenses
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE expenses IS 'Spese generiche (foglio Spese). Le spese carte sono in card_purchases.';
COMMENT ON COLUMN expenses.related_to_cards IS
    'Se TRUE, questa spesa va sottratta anche dal profitto netto delle carte sciolte.';
COMMENT ON COLUMN expenses.category IS
    'Tag libero: spedizioni, materiali, sleeves, deck box, fee account, viaggi, altro';
