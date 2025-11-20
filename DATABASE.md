# Guida Database per NerdNostalgia

Documentazione completa del sistema database di NerdNostalgia.

## Panoramica

NerdNostalgia utilizza **SQLAlchemy 2.0** come ORM e **Alembic** per le migrations. Il database traccia:
- Utenti e loro permessi
- Articoli (inventario)
- Listing (pubblicazioni su piattaforme)
- Storico modifiche
- Statistiche e analytics

### Tecnologie

- **SQLAlchemy 2.0**: ORM Python moderno e performante
- **Alembic**: Sistema di migrations per schema evolution
- **SQLite**: Database di default (facile setup, zero configurazione)
- **PostgreSQL**: Supportato per produzione (scalabilità e performance)

## Schema Database

### Tabelle Principali

#### 1. `users` - Utenti
Gestisce gli utenti del sistema.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| id | Integer (PK) | ID univoco utente |
| username | String(100) | Username univoco |
| email | String(255) | Email univoca |
| full_name | String(255) | Nome completo |
| role | Enum | admin / user |
| is_active | Boolean | Utente attivo |
| created_at | DateTime | Data creazione |
| updated_at | DateTime | Data ultimo aggiornamento |

#### 2. `items` - Articoli
Inventario degli articoli da vendere.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| id | Integer (PK) | ID univoco articolo |
| user_id | Integer (FK) | Proprietario |
| title | String(255) | Titolo articolo |
| description | Text | Descrizione completa |
| price | Decimal(10,2) | Prezzo |
| quantity | Integer | Quantità disponibile |
| category | String(100) | Categoria |
| condition | Enum | new/used/refurbished/for_parts |
| sku | String(100) | SKU univoco |
| brand | String(100) | Brand/marca |
| images | Text (JSON) | Array di path immagini |
| tags | Text (JSON) | Array di tags |
| shipping_weight | Float | Peso spedizione (kg) |
| created_at | DateTime | Data creazione |
| updated_at | DateTime | Data ultimo aggiornamento |

#### 3. `platforms` - Piattaforme
Piattaforme e-commerce supportate.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| id | Integer (PK) | ID univoco piattaforma |
| name | String(50) | Nome interno (ebay, amazon) |
| display_name | String(100) | Nome visualizzato |
| is_active | Boolean | Piattaforma attiva |
| config | Text (JSON) | Configurazione specifica |
| created_at | DateTime | Data creazione |

**Piattaforme predefinite:**
- eBay
- Amazon
- Subito.it
- Vinted

#### 4. `listings` - Listing
Articoli pubblicati sulle piattaforme.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| id | Integer (PK) | ID univoco listing |
| item_id | Integer (FK) | Articolo pubblicato |
| platform_id | Integer (FK) | Piattaforma |
| user_id | Integer (FK) | Utente proprietario |
| platform_item_id | String(255) | ID sulla piattaforma |
| url | String(500) | URL del listing |
| status | Enum | draft/active/sold/ended/error |
| listed_price | Decimal(10,2) | Prezzo di pubblicazione |
| views_count | Integer | Numero visualizzazioni |
| watchers_count | Integer | Numero osservatori |
| published_at | DateTime | Data pubblicazione |
| ended_at | DateTime | Data fine |
| sold_at | DateTime | Data vendita |
| created_at | DateTime | Data creazione |
| updated_at | DateTime | Data ultimo aggiornamento |

#### 5. `listing_history` - Storico Listing
Log di tutte le modifiche ai listing.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| id | Integer (PK) | ID univoco |
| listing_id | Integer (FK) | Listing associato |
| event_type | String(50) | Tipo evento |
| event_data | Text (JSON) | Dati dell'evento |
| notes | Text | Note aggiuntive |
| created_at | DateTime | Data evento |

**Tipi di eventi:**
- `created`: Listing creato
- `updated`: Listing aggiornato
- `status_changed`: Cambio stato
- `price_changed`: Cambio prezzo
- `sold`: Venduto
- `ended`: Terminato

### Relazioni

```
User 1──── Items
User 1──── Listings

Item 1──── Listings

Platform 1──── Listings

Listing 1──── ListingHistory
```

### Indici

Indici ottimizzati per query comuni:
- `idx_listings_user_platform_status`: User + Platform + Status
- `idx_items_user_category`: User + Category
- `idx_history_listing_event`: Listing + Event Type

## Inizializzazione

### Setup Iniziale

```bash
# Crea il database e le tabelle
python main.py db init

# Crea primo utente
python main.py db create-user
# Username: admin
# Email: admin@example.com
```

### Con Docker

```bash
# Inizializza database
./docker-run.sh shell
python main.py db init
exit
```

## Comandi CLI

### Database Management

```bash
# Inizializza database
python main.py db init

# Reset database (ATTENZIONE: elimina tutti i dati!)
python main.py db reset
```

### Gestione Utenti

```bash
# Crea utente
python main.py db create-user

# Con parametri
python main.py db create-user \
  --username johndoe \
  --email john@example.com \
  --full-name "John Doe"
```

### Query Dati

```bash
# Lista tutti gli articoli
python main.py db list-items

# Lista articoli per utente
python main.py db list-items --user-id 1

# Lista listing
python main.py db list-listings

# Lista listing attivi
python main.py db list-listings --status active

# Lista listing per piattaforma
python main.py db list-listings --platform ebay

# Filtra per utente e piattaforma
python main.py db list-listings --user-id 1 --platform ebay

# Statistiche utente
python main.py db stats --user-id 1
```

## Usage in Code

### DatabaseManager

```python
from src.database.manager import DatabaseManager
from src.database.models import ItemCondition, ListingStatus

# Inizializza
db = DatabaseManager('sqlite:///data/nerdnostalgia.db')
db.create_tables()

# Crea utente
user = db.create_user(
    username='mario',
    email='mario@example.com',
    full_name='Mario Rossi'
)

# Crea articolo
item = db.create_item(
    user_id=user.id,
    item_data={
        'title': 'PlayStation 5',
        'description': 'Console nuova, mai usata',
        'price': 499.99,
        'quantity': 1,
        'category': 'gaming',
        'condition': 'new',
        'sku': 'PS5-001',
        'brand': 'Sony',
        'images': ['ps5_1.jpg', 'ps5_2.jpg'],
        'tags': ['gaming', 'console', 'ps5']
    }
)

# Crea listing (dopo pubblicazione su eBay)
listing = db.create_listing(
    item_id=item.id,
    platform_name='ebay',
    platform_item_id='123456789',  # ID eBay
    listed_price=499.99,
    url='https://ebay.it/itm/123456789'
)

# Aggiorna stato listing
db.update_listing_status(
    listing.id,
    ListingStatus.SOLD,
    notes='Venduto in 3 giorni'
)

# Query
items = db.list_items(user_id=user.id)
active_listings = db.list_listings(
    user_id=user.id,
    status=ListingStatus.ACTIVE
)

# Statistiche
stats = db.get_user_stats(user.id)
print(f"Articoli: {stats['total_items']}")
print(f"Venduti: {stats['sold_listings']}")
```

### Sessioni SQLAlchemy

Per query avanzate:

```python
from src.database.models import User, Item, Listing

db = DatabaseManager()

# Usa sessione
with db.get_session() as session:
    # Query complessa
    results = (
        session.query(Item, Listing)
        .join(Listing)
        .filter(Listing.status == ListingStatus.ACTIVE)
        .filter(Item.price > 100)
        .all()
    )

    for item, listing in results:
        print(f"{item.title} - {listing.platform.name}")
```

## Migrations con Alembic

### Creare una Migration

```bash
# Autogenera migration da modifiche modelli
alembic revision --autogenerate -m "Add field to items"

# Crea migration vuota
alembic revision -m "Custom migration"
```

### Applicare Migrations

```bash
# Applica tutte le migrations
alembic upgrade head

# Applica fino a specifica revision
alembic upgrade <revision_id>

# Rollback ultima migration
alembic downgrade -1

# Rollback a specifica revision
alembic downgrade <revision_id>
```

### Info Migrations

```bash
# Mostra storia migrations
alembic history

# Mostra revision corrente
alembic current

# Mostra SQL che verrà eseguito (dry-run)
alembic upgrade head --sql
```

## Database per Ambiente

### Sviluppo (SQLite)

```python
db = DatabaseManager('sqlite:///data/nerdnostalgia.db')
```

### Produzione (PostgreSQL)

```python
db = DatabaseManager(
    'postgresql://user:password@localhost:5432/nerdnostalgia'
)
```

### Da Variabile Ambiente

```python
import os
db_url = os.getenv('DATABASE_URL', 'sqlite:///data/nerdnostalgia.db')
db = DatabaseManager(db_url)
```

### Configurazione alembic.ini

Per PostgreSQL, modifica `alembic.ini`:

```ini
sqlalchemy.url = postgresql://user:password@localhost:5432/nerdnostalgia
```

## Query Comuni

### Articoli più venduti

```python
from sqlalchemy import func

with db.get_session() as session:
    top_items = (
        session.query(
            Item.title,
            func.count(Listing.id).label('sales')
        )
        .join(Listing)
        .filter(Listing.status == ListingStatus.SOLD)
        .group_by(Item.id)
        .order_by(func.count(Listing.id).desc())
        .limit(10)
        .all()
    )
```

### Guadagno totale per utente

```python
from sqlalchemy import func

with db.get_session() as session:
    revenue = (
        session.query(func.sum(Listing.listed_price))
        .filter(Listing.user_id == user_id)
        .filter(Listing.status == ListingStatus.SOLD)
        .scalar()
    )
```

### Listing attivi per piattaforma

```python
from sqlalchemy import func

with db.get_session() as session:
    stats = (
        session.query(
            Platform.name,
            func.count(Listing.id)
        )
        .join(Listing)
        .filter(Listing.status == ListingStatus.ACTIVE)
        .group_by(Platform.name)
        .all()
    )
```

## Best Practices

### 1. Usa Context Manager per Sessioni

```python
# CORRETTO
with db.get_session() as session:
    user = session.query(User).first()
    # usa user...
# sessione chiusa automaticamente

# EVITA
session = db.get_session()
user = session.query(User).first()
# sessione non chiusa!
```

### 2. Gestisci le Transazioni

```python
with db.get_session() as session:
    try:
        item = Item(...)
        session.add(item)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Errore: {e}")
```

### 3. Usa gli Helper del DatabaseManager

```python
# PREFERITO
item = db.create_item(user_id=1, item_data={...})

# Invece di
with db.get_session() as session:
    item = Item(...)
    session.add(item)
    session.commit()
```

### 4. Evita N+1 Query Problem

```python
# BAD: N+1 query
items = session.query(Item).all()
for item in items:
    print(item.user.username)  # Query per ogni item!

# GOOD: Eager loading
from sqlalchemy.orm import joinedload

items = (
    session.query(Item)
    .options(joinedload(Item.user))
    .all()
)
for item in items:
    print(item.user.username)  # Nessuna query aggiuntiva
```

## Backup e Restore

### SQLite

```bash
# Backup
cp data/nerdnostalgia.db data/backup_$(date +%Y%m%d).db

# Restore
cp data/backup_20250101.db data/nerdnostalgia.db
```

### PostgreSQL

```bash
# Backup
pg_dump nerdnostalgia > backup.sql

# Restore
psql nerdnostalgia < backup.sql
```

## Troubleshooting

### Database locked (SQLite)

```bash
# Controlla processi che usano il database
lsof data/nerdnostalgia.db

# O ricrea database
python main.py db reset
python main.py db init
```

### Migration conflict

```bash
# Mostra conflitto
alembic history

# Risolvi manualmente o reset
rm alembic/versions/*.py
alembic revision --autogenerate -m "Initial migration"
```

### Performance lente

1. Aggiungi indici appropriati
2. Usa eager loading (joinedload)
3. Considera PostgreSQL per produzione
4. Ottimizza query con EXPLAIN

## Risorse

- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [PostgreSQL](https://www.postgresql.org/)
- [SQLite](https://www.sqlite.org/)
