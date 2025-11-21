-- Tabella User per NerdNostalgia
-- Database: PostgreSQL

-- Creazione tipo ENUM per i ruoli utente
CREATE TYPE user_role AS ENUM ('ADMIN', 'USER', 'GUEST');

-- Creazione tabella users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role user_role NOT NULL DEFAULT 'USER',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indici per migliorare le performance delle query
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);

-- Trigger per aggiornare automaticamente updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Commenti sulle colonne
COMMENT ON TABLE users IS 'Tabella utenti del sistema NerdNostalgia';
COMMENT ON COLUMN users.id IS 'ID univoco utente';
COMMENT ON COLUMN users.username IS 'Username univoco per login';
COMMENT ON COLUMN users.email IS 'Email univoca utente';
COMMENT ON COLUMN users.hashed_password IS 'Password hashata (bcrypt/argon2)';
COMMENT ON COLUMN users.full_name IS 'Nome completo utente';
COMMENT ON COLUMN users.role IS 'Ruolo utente: admin, user, guest';
COMMENT ON COLUMN users.is_active IS 'Indica se l''utente � attivo';
COMMENT ON COLUMN users.is_verified IS 'Indica se l''email � stata verificata';
COMMENT ON COLUMN users.created_at IS 'Data e ora di creazione';
COMMENT ON COLUMN users.updated_at IS 'Data e ora ultimo aggiornamento';
