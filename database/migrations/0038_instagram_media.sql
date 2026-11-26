-- Instagram: ogni post, Storia e Reel pubblicato (da noi o, per lo storico,
-- dall'app) con le sue statistiche. Serve a scegliere orari e hashtag che
-- raggiungono piu' persone. Vedi utils/instagram_stats.py.
CREATE TABLE IF NOT EXISTS instagram_media (
    media_id VARCHAR(40) PRIMARY KEY,
    kind VARCHAR(10) NOT NULL,
    published_at TIMESTAMP NOT NULL,
    slot VARCHAR(5),
    n_items INTEGER NOT NULL DEFAULT 1,
    fallback BOOLEAN NOT NULL DEFAULT 0,
    hashtags TEXT NOT NULL DEFAULT '',
    reach INTEGER,
    views INTEGER,
    saved INTEGER,
    shares INTEGER,
    interactions INTEGER,
    insights_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_instagram_media_published ON instagram_media(published_at);
