# NerdNostalgia

Vetrina pubblica + pannello admin per gestire vendite di carte, videogiochi, fumetti & co.
Inventario lotti, sync Vinted/eBay, dashboard bilancio, contovendita.

**Stack**: Next.js 15 (App Router) · FastAPI · SQLite · Docker Compose · Caddy (in prod via [garganacl](https://github.com/danielebucchi/garganacl) Ansible)

## Quick start (sviluppo locale)

Prerequisiti: Docker Desktop. Niente Python/Node sull'host.

```bash
git clone https://github.com/danielebucchi/NerdNostalgia
cd NerdNostalgia

# Dev mode (hot reload frontend + bind mount backend)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Apri http://localhost:3737
# Backend: http://localhost:7373/docs (OpenAPI Swagger)
```

Stop:
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

## Quick start (prod-like in locale)

```bash
docker compose up -d --build
```

Stessa cosa con `Dockerfile.prod` per il frontend (next build + standalone) e niente bind mount del codice.

## Login admin

DB SQLite di sviluppo: `data/nerdnostalgia.db`. Dopo `docker compose up`, il backend
applica `database/schema.sql` + migrazioni in `database/migrations/`.

La migrazione `0001_seed_initial.sql` crea l'admin di default:
- **username**: `admin`
- **password**: `changeme` — **cambiala subito** in produzione

### Creare/aggiornare admin in produzione

POST `/api/users/` è **admin-only**: il primissimo admin viene dalla seed migration
(username `admin`, password `changeme`). Per gli altri usa lo script CLI:

```bash
# Crea nuovo admin
docker exec -it nerdnostalgia-backend python /app/scripts/create_admin.py \
  --username daniele --email daniele@example.com
# Prompt password interattivo (oppure --password "...")

# Aggiorna password di un admin esistente
docker exec -it nerdnostalgia-backend python /app/scripts/create_admin.py \
  --username admin --email admin@example.com --update
```

Per il quick-and-dirty senza script:
```bash
docker exec -it nerdnostalgia-backend python -c \
  "from utils.security import hash_password; print(hash_password('la-tua-password'))"
docker exec -it nerdnostalgia-backend sqlite3 /app/data/nerdnostalgia.db \
  "UPDATE users SET hashed_password='<paste-hash>' WHERE username='admin'"
```

## Test

```bash
# Backend (pytest + coverage)
docker exec -w /app nerdnostalgia-backend python -m pytest tests/
# Equivalente locale: cd backend && pip install -r requirements-test.txt && pytest

# Frontend (Vitest + jsdom + RTL)
docker exec -w /app nerdnostalgia-frontend npm run test:run
# Equivalente locale: cd frontend && npm test
```

CI: workflow `.github/workflows/ci.yml` gira automaticamente su push/PR su `main`.

## Layout

```
backend/
  src/
    api/           # Endpoint FastAPI (articles, lots, inventory, dashboard, …)
    helpers/       # Logica business (uno per modello)
    models/db/     # Modelli SQLAlchemy
    models/entities/  # Pydantic schemas in/out
    utils/         # session, security (JWT), scheduler, backup, email, limiter
  tests/
    integration/   # FastAPI TestClient + SQLite in-memory + admin seedato
    unit/          # Test puri senza DB
  Dockerfile
  entrypoint.sh    # applica schema.sql + migrations e avvia uvicorn

frontend/
  src/
    app/
      (public)/    # Vetrina pubblica (catalogo, contatti)
      admin/       # Pannello admin
    components/    # Shared components React
    lib/           # api client, hooks, types
  Dockerfile       # Dev mode (next dev)
  Dockerfile.prod  # next build + standalone runtime
  __tests__/

database/
  schema.sql              # Schema consolidato SQLite
  migrations/             # Migrazioni incrementali numerate (0001_…sql)
  _legacy_postgres/       # Storia: vecchie migrazioni PG (riferimento)

scripts/
  migrate_pg_to_sqlite.py # Script one-shot, eseguito durante la migrazione

.github/
  workflows/ci.yml
  dependabot.yml
```

## Deploy in produzione

Single-node Hetzner via [garganacl](https://github.com/danielebucchi/garganacl) (Ansible).
Provisioning automatico:
- Caddy + Let's Encrypt (HTTPS automatico)
- UFW + fail2ban + unattended-upgrades
- Docker + compose
- Prometheus + Grafana + ntfy
- Deployer generico che fa `git clone` + `docker compose up -d`

L'app NerdNostalgia è già definita in `inventory/group_vars/all/apps.yml` di garganacl.

Vedi [ARCHITECTURE.md](ARCHITECTURE.md) per i dettagli.

## Backup

Job APScheduler gira ogni giorno alle 03:30 (Europe/Rome) e:
1. Snapshot SQLite consistente in `data/backups/nerdnostalgia-YYYYMMDD-HHMMSS.db`
2. Tar dei file uploadati in `data/backups/uploads-YYYYMMDD-HHMMSS.tar.gz`
3. Prune retention > 30 giorni
4. Opzionale: upload su S3/R2 se `BACKUP_S3_BUCKET` env e' settato (richiede `boto3`)

## Variabili d'ambiente

Copia `.env.example` in `.env` e personalizza. Le principali:

| Var | Default | Cosa fa |
|---|---|---|
| `JWT_SECRET_KEY` | `dev-secret-change-me` | Firma dei token JWT — **CAMBIA in prod** |
| `EMAIL_ENABLED` | `0` | Abilita invio email (notifiche inquiries) |
| `SMTP_USER/PASSWORD` | empty | Gmail App Password |
| `BACKUP_S3_BUCKET` | empty | Se valorizzato, upload backup su S3/R2 |
| `TZ` / `APP_TIMEZONE` | `Europe/Rome` | Timezone della macchina e dello scheduler |
| `DISABLE_SCHEDULER` | empty | Set a `1` per disabilitare APScheduler |

## Dev tooling

```bash
# Pre-commit hooks (ruff lint+format, prettier, etc)
pip install pre-commit
pre-commit install

# Dependabot auto-PR settimanali su pip/npm/actions/docker
# (config in .github/dependabot.yml)
```

## License

Personal project. All rights reserved.
