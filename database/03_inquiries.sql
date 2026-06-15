-- Tabella Inquiries (richieste contatto) per NerdNostalgia
-- Database: PostgreSQL

CREATE TYPE inquiry_status AS ENUM ('NEW', 'READ', 'REPLIED', 'CLOSED');

CREATE TABLE IF NOT EXISTS inquiries (
    id SERIAL PRIMARY KEY,
    article_id INTEGER NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    subject VARCHAR(255),
    message TEXT NOT NULL,
    status inquiry_status NOT NULL DEFAULT 'NEW',
    ip_address VARCHAR(45),
    admin_notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    replied_at TIMESTAMP,

    CONSTRAINT fk_inquiry_article
        FOREIGN KEY(article_id)
        REFERENCES articles(id)
        ON DELETE SET NULL
);

CREATE INDEX idx_inquiries_status ON inquiries(status);
CREATE INDEX idx_inquiries_article_id ON inquiries(article_id);
CREATE INDEX idx_inquiries_email ON inquiries(email);
CREATE INDEX idx_inquiries_created_at ON inquiries(created_at DESC);

CREATE TRIGGER update_inquiries_updated_at
    BEFORE UPDATE ON inquiries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE inquiries IS 'Richieste di contatto / informazioni dai visitatori';
COMMENT ON COLUMN inquiries.article_id IS 'ID articolo a cui si riferisce la richiesta (NULL = contatto generico)';
COMMENT ON COLUMN inquiries.status IS 'NEW = da leggere, READ = letta, REPLIED = risposta inviata, CLOSED = chiusa';
COMMENT ON COLUMN inquiries.ip_address IS 'IP del mittente per anti-abuso (best effort)';
COMMENT ON COLUMN inquiries.admin_notes IS 'Note interne admin sulla richiesta';
