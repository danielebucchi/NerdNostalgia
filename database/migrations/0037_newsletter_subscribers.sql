-- Iscritti alla newsletter senza account (doppio opt-in: valgono solo dopo
-- la conferma dal link nell'email). Vedi models/db/newsletter_subscriber.py.
CREATE TABLE IF NOT EXISTS newsletter_subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) NOT NULL UNIQUE,
    confirm_token VARCHAR(64),
    confirm_sent_at TIMESTAMP,
    confirmed_at TIMESTAMP,
    revoked_at TIMESTAMP,
    unsubscribe_token VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_newsletter_subscribers_confirm
    ON newsletter_subscribers(confirm_token);
