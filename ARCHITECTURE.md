# Architecture

Sito monolitico a single tenant. **Un utente admin** (tu) che gestisce inventario e vetrina, **N visitatori pubblici** che vedono il catalogo e inviano richieste.

## Bird's eye

```
                Internet
                    |
              Cloudflare DNS
                    |
                    ▼
            ┌─────────────┐
            │    Caddy    │  HTTPS auto (Let's Encrypt)
            │ (in prod)   │  reverse proxy single-port
            └──────┬──────┘
                   │
        ┌──────────┼──────────────┐
        ▼                         ▼
  nerdnostalgia.it      api.nerdnostalgia.it
        │                         │
        ▼                         ▼
   ┌─────────┐               ┌────────┐
   │ Next.js │ (3737)        │FastAPI │ (7373)
   │ App Rtr │               │uvicorn │
   └─────────┘               └────┬───┘
                                  │
                       ┌──────────┴──────────┐
                       │                     │
                       ▼                     ▼
                  ┌────────┐        ┌──────────────┐
                  │ SQLite │        │ tmp/uploads/ │
                  │ data/  │        │ (bind mount) │
                  └────────┘        └──────────────┘
```

In **prod** (Hetzner via garganacl): Caddy fa il bridge HTTPS pubblico, app bindate `127.0.0.1`.
In **dev** (Mac via docker compose): apri direttamente `localhost:3737` (frontend) e `localhost:7373` (backend).

## Tecnologie

| Layer | Scelta | Perché |
|---|---|---|
| **Frontend** | Next.js 15 App Router + TS | SSR-ready, file-based routing, output standalone per Docker |
| | Tailwind 3 | utility-first, no Setup-CSS, dark mode pronta |
| | recharts | grafici dashboard (donuts, bars, composed) |
| | @dnd-kit | drag & drop riordino articoli/lotti |
| **Backend** | FastAPI | typed API, OpenAPI auto, DI bella |
| | SQLAlchemy 2.0 | ORM type-safe, portable PG/SQLite |
| | Pydantic V2 | schema in/out validati |
| | APScheduler | cron in-process (no system cron, no Celery overhead) |
| | Playwright | scraping Vinted headless |
| | slowapi | rate limit `/api/inquiries` |
| | passlib + bcrypt | hash password |
| | python-jose | JWT |
| **DB** | SQLite | un file → backup banale, single-user fit perfetto |
| **Auth** | JWT Bearer + OAuth2 password flow | endpoint admin protetti, pubblico aperto |
| **Container** | Docker Compose | dev e prod stesso file (con overlay dev) |
| **HTTPS** | Caddy (esterno via garganacl) | cert Let's Encrypt automatico, zero config |
| **Backup** | APScheduler daily job | snapshot SQLite + tar uploads, optional S3 |
| **Monitoring** | Prometheus + Grafana + ntfy (garganacl) | dashboard + alert push |

## Frontend

### Routing

```
src/app/
├── (public)/                       # Group: pagine senza auth
│   ├── page.tsx                    # homepage / vetrina
│   ├── articles/[id]/              # dettaglio articolo + form inquiry
│   ├── wanted/                     # cerco/compro
│   └── contatti/
├── admin/
│   ├── layout.tsx                  # AdminShell con sidebar/topbar
│   ├── page.tsx                    # Dashboard collapsible sections
│   ├── articles/                   # CRUD articoli
│   ├── lotti/                      # Lots: list, drill-down, wizard, search
│   ├── inventory/                  # raramente usato direttamente
│   ├── vendite/                    # HUB con 4 tab
│   │   ├── esterne/
│   │   ├── creazioni/
│   │   ├── contovendita/
│   │   └── carte/
│   ├── spese/                      # 2 tab: Spese carte | Altre spese
│   ├── inquiries/                  # richieste ricevute
│   ├── wanted/                     # gestione cerco/compro
│   ├── tassonomia/                 # 2 tab: Categorie | Piattaforme
│   ├── import-vinted/              # status sync Vinted
│   ├── markups/                    # commissioni marketplace
│   └── login/
├── layout.tsx                      # root layout + metadata SEO
├── sitemap.ts                      # sitemap.xml auto
├── robots.ts                       # robots.txt auto
├── icon.png + apple-icon.png + favicon.ico
└── globals.css
```

### Stato

- Niente Redux/Zustand. Per cose lato client si usa `useState` + custom hooks (`useArticles`, `usePlatforms`, …).
- localStorage per: wishlist pubblica, stato collapsible dashboard (key prefix `nn:dash:collapse:`).
- Auth admin: JWT in `localStorage` via `AuthProvider`.

### Build modes

| Modo | Comando | Quando |
|---|---|---|
| Dev | `next dev -p 3737` | hot reload, source maps, no optim |
| Prod | `next build` + `next start` (o `node server.js` standalone) | bundle minimo, immagini ottimizzate, RSC streaming |

## Backend

### Layered architecture

```
api/        endpoint FastAPI (router + Pydantic in/out)
   ↓ Depends
helpers/    business logic (uno per dominio)
   ↓
models/db/  SQLAlchemy ORM
   ↓
schema.sql  schema dichiarativo SQLite
```

### Domini

| Dominio | Endpoint | DB tables | Note |
|---|---|---|---|
| **auth** | `/api/auth/login`, `/me` | `users` | JWT 60min |
| **users** | `/api/users/` | `users` | admin-only |
| **articles** | `/api/articles/` | `articles`, `categories` | catalogo pubblico + admin |
| **categories** | `/api/categories/` | `categories` | gerarchia parent_id |
| **inquiries** | `/api/inquiries/` | `inquiries` | POST pubblico, rate-limited 5/min |
| **wanted** | `/api/wanted/` | `wanted_items` | cerco/compro |
| **lots** | `/api/lots/` | `lots` | auto-code L0001, status enum |
| **inventory** | `/api/inventory/` | `inventory_items` | items dentro lot |
| **dashboard** | `/api/dashboard/totali` | aggregati su tutto | breakdown per anno/categoria/piattaforma |
| **vendite esterne** | `/api/misc-sales/?kind=external` | `misc_sales` | discriminator `kind` |
| **creazioni** | `/api/misc-sales/?kind=creation` | `misc_sales` | con `material_cost` |
| **contovendita** | `/api/consignment-sales/` | `consignment_sales` | + mark-paid |
| **personal-cards** | `/api/personal-cards/` | `personal_cards` | carte sciolte (stock + vendita) |
| **expenses** | `/api/expenses/` | `expenses` | con flag `related_to_cards/creations` |
| **platforms** | `/api/platforms/` | `platforms` | vendita + acquisto (unico) |
| **marketplace-fees** | `/api/marketplace-fees/` | `marketplace_fees` | markup % per piattaforma+categoria |
| **vinted** | `/api/vinted/` | `vinted_settings`, `vinted_sync_logs` | sync giornaliera via Playwright |

### Scheduler

`APScheduler` con timezone `Europe/Rome`. Due cron:
1. **Vinted sync** — `:05` ogni ora, controlla se l'ora coincide con `vinted_settings.sync_hour` (default 04) → dedup giornaliero
2. **Daily backup** — `03:30` → snapshot SQLite + tar uploads + prune > 30gg

Disabilitabile con `DISABLE_SCHEDULER=1` (tipicamente nei test).

### Rate limit

`slowapi` con `get_remote_address` come key. Solo `/api/inquiries/` POST: **5/min, 30/h** per IP. Honeypot field `website` rigetta silenziosamente.

## Database

SQLite singolo file. **No Postgres** dopo la migrazione storica.

Caratteristiche:
- File: `data/nerdnostalgia.db` (bind-mounted, nel piano backup)
- Schema in `database/schema.sql` consolidato (idempotente `IF NOT EXISTS`)
- Migrazioni incrementali in `database/migrations/` numerate `NNNN_descrizione.sql`
  - Tabella `schema_migrations(version, applied_at)` traccia quelle applicate
  - Entrypoint del backend applica schema + migrations pending a ogni avvio
- `_legacy_postgres/` contiene le vecchie migrazioni PG (riferimento storico)

### Modelli principali (relazioni)

```
                  ┌─────────┐
                  │  users  │
                  └────┬────┘
                       │ 1:N
                       ▼
                  ┌──────────┐    N:1   ┌────────────┐
                  │ articles │─────────►│ categories │
                  └─────┬────┘          └─────┬──────┘
                        │ 1:N                 ▲
                        ▼                     │ N:1
                  ┌─────────────┐             │
                  │ inquiries   │             │
                  └─────────────┘             │
                                              │
        ┌─────┐  1:N    ┌──────────────────┐ │
        │ lots│─────────► inventory_items  │─┘
        └─────┘         │  (N:1 → articles)│
                        └──────────────────┘

  // Tabelle "indipendenti" senza FK forti:
  // misc_sales, consignment_sales, personal_cards, expenses,
  // platforms, marketplace_fees, vinted_settings, vinted_sync_logs, wanted_items
```

## Test

- **Backend**: pytest + httpx TestClient + SQLite in-memory (StaticPool, fresh per test). 63+ test integration, 9 unit puri. Coverage report XML.
- **Frontend**: Vitest + jsdom + React Testing Library. 13 test su componenti con stato (CollapsibleSection, InquiryDialog).
- **CI**: `.github/workflows/ci.yml` su push/PR `main`. Backend pytest + frontend vitest + tsc check.

Fixtures conftest:
- `engine` (per-test, in-memory) → `db_session` → override `get_db`
- `admin_user` seedato → `admin_token` JWT → `admin_headers`
- `limiter.reset()` fra test (slowapi storage in-memory globale)

## Operations

### Dev locale

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
# Volume mount: ./backend → /app, ./frontend → /app
# Hot reload backend (uvicorn restart non automatico — restart manuale necessario)
# Hot reload frontend (next dev watch via WATCHPACK_POLLING)
```

### Prod (single-node Hetzner)

```bash
# Sul VPS (provisioning fatto da garganacl Ansible):
cd /opt/apps/nerdnostalgia   # garganacl clona qui
docker compose up -d --build  # usa docker-compose.yml (prod)

# Aggiornamento codice:
git pull && docker compose up -d --build  # ricostruisce immagini cambiate
```

### Backup restore

```bash
# Stop backend
docker compose stop backend

# Sostituisci file DB
cp data/backups/nerdnostalgia-YYYYMMDD-HHMMSS.db data/nerdnostalgia.db

# Restore uploads
tar -xzf data/backups/uploads-YYYYMMDD-HHMMSS.tar.gz -C tmp/

# Restart
docker compose up -d backend
```

### Migrazioni schema

Quando devi modificare lo schema (es. nuova colonna, nuova tabella):

1. Aggiungi un file in `database/migrations/NNNN_descrizione.sql` con `IF NOT EXISTS` ovunque possibile
2. Modifica anche `database/schema.sql` (so new installs start with the right schema)
3. Modifica modelli SQLAlchemy in `backend/src/models/db/`
4. Aggiungi entities Pydantic in `backend/src/models/entities/`
5. Test in locale (rebuild backend container)
6. Commit + push → garganacl deploy → migrazioni applicate automaticamente al riavvio

**Non modificare `schema.sql` con `ALTER TABLE`**: SQLite non supporta tutte le `ALTER`. Aggiungi la migration incrementale, e in `schema.sql` aggiorna direttamente la `CREATE TABLE` per i nuovi deploy.

## Decisioni e tradeoff

- **SQLite vs Postgres**: scelto SQLite perche' app single-user, backup = `cp file`, deploy senza container DB. Trade-off: niente FTS in italiano (sostituito da `LIKE/ILIKE`).
- **Dev container vs venv**: scelto container per uniformare con prod. Setup zero su host (no Python/Node richiesti).
- **Monolite vs micro-servizi**: monolite ovvio per traffico atteso (singolo utente admin + qualche centinaio di visitatori/mese).
- **JWT vs session cookie**: JWT per semplicità (un solo admin), localStorage frontend. Per multi-utente sarebbe meglio cookie HttpOnly.
- **Backup APScheduler vs Litestream**: scelto snapshot daily perche' RPO 24h e' OK per side-project. Litestream avrebbe RPO ~secondi ma richiede S3/R2 sempre.
