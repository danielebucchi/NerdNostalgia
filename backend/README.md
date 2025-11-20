# NerdNostalgia Backend

Backend API per il sistema NerdNostalgia - gestione e pubblicazione articoli su piattaforme e-commerce.

## Setup con Docker (Raccomandato)

### Avvio Rapido

```bash
# Dalla root del progetto
docker-compose up --build
```

Questo comando:
1. Avvia il container PostgreSQL
2. Esegue automaticamente gli script SQL in `database/user.sql` (solo alla prima inizializzazione)
3. Avvia il backend che esegue le migrazioni Alembic
4. L'API sarà disponibile su http://localhost:7373

### Come Funziona

**Container Database (db):**
- PostgreSQL 15
- Esegue automaticamente tutti i file `.sql` in `./database/` all'inizializzazione
- I dati sono persistenti nel volume `db_data`
- Healthcheck: verifica che il database sia pronto prima di avviare il backend

**Container Backend:**
- Python 3.13
- Script `entrypoint.sh`:
  1. Attende che PostgreSQL sia ready (`pg_isready`)
  2. Esegue migrazioni Alembic (`alembic upgrade head`)
  3. Avvia l'applicazione FastAPI

**Ordine di avvio:**
1. `db` container → esegue `database/user.sql`
2. Attende healthcheck (PostgreSQL ready)
3. `backend` container → esegue migrazioni Alembic → avvia API

### Comandi Utili Docker

```bash
# Avvia tutti i servizi
docker-compose up -d

# Vedi i logs
docker-compose logs -f

# Vedi logs solo del database
docker-compose logs -f db

# Vedi logs solo del backend
docker-compose logs -f backend

# Ferma tutti i servizi
docker-compose down

# Ferma e rimuovi anche i volumi (ATTENZIONE: elimina il database!)
docker-compose down -v

# Rebuild dei container
docker-compose up --build

# Accedi al database PostgreSQL
docker exec -it nerdnostalgia_db psql -U user -d nerdnostalgia
```

## Setup Locale (senza Docker)

### 1. Installazione Dipendenze

```bash
cd backend
pip install -r src/requirements.txt
```

### 2. Configurazione Database

Crea un file `.env` nella directory backend:

```bash
cp .env.example .env
```

Modifica con le tue credenziali PostgreSQL:
```
DATABASE_URL=postgresql://user:password@localhost:5432/nerdnostalgia
```

### 3. Creazione Database

Esegui manualmente gli script SQL:
```bash
psql -U user -d nerdnostalgia -f database/user.sql
```

### 4. Esecuzione Migrazioni

```bash
cd backend
alembic upgrade head
```

### 5. Avvio Applicazione

```bash
python src/main.py
# oppure
uvicorn src.main:app --reload --host 0.0.0.0 --port 7373
```

## Struttura Database

### Tabella Users

Il modello SQLAlchemy si trova in: `backend/src/models/db/user.py`

**Campi:**
- `id` (Integer, Primary Key)
- `username` (String 100, unique, indexed)
- `email` (String 255, unique, indexed)
- `hashed_password` (String 255)
- `full_name` (String 255, optional)
- `role` (Enum: ADMIN, USER, GUEST, default: USER)
- `is_active` (Boolean, default: True)
- `is_verified` (Boolean, default: False)
- `created_at` (DateTime, auto)
- `updated_at` (DateTime, auto-update)

## Alembic - Gestione Migrazioni

### Creare una Nuova Migrazione

Dopo aver modificato i modelli in `src/models/db/`:

```bash
# Con PostgreSQL configurato:
alembic revision --autogenerate -m "Descrizione della modifica"

# Oppure con SQLite temporaneo:
DATABASE_URL="sqlite:///./temp.db" alembic revision --autogenerate -m "Descrizione"
```

### Applicare le Migrazioni

```bash
alembic upgrade head
```

### Rollback Migrazione

```bash
# Rollback dell'ultima migrazione
alembic downgrade -1

# Rollback a una revisione specifica
alembic downgrade <revision_id>
```

### Vedere lo Storico Migrazioni

```bash
alembic history
alembic current
```

## Query SQL

Le query SQL grezze per PostgreSQL si trovano in:
- `database/user.sql` - Tabella users con trigger e indici

## Note

- Il modello SQLAlchemy e le migrazioni Alembic sono già sincronizzati
- La variabile `DATABASE_URL` nel file `.env` viene letta automaticamente da `alembic/env.py`
- Per sviluppo locale puoi usare SQLite, per produzione usa PostgreSQL
