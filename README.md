# NerdNostalgia

Sistema di gestione e pubblicazione articoli su piattaforme di e-commerce.

## Descrizione

NerdNostalgia è un'applicazione Python che permette di:
- Importare articoli da file CSV
- Pubblicare articoli su piattaforme e-commerce (eBay, e altre in futuro)
- Gestire l'inventario e le pubblicazioni
- Interfaccia grafica (in sviluppo futuro)

## Struttura del Progetto

```
NerdNostalgia/
├── src/
│   ├── models/          # Modelli dati per articoli e prodotti
│   ├── parsers/         # Parser per CSV e altri formati
│   ├── platforms/       # Integrazioni con piattaforme e-commerce
│   │   └── ebay/        # Integrazione eBay
│   ├── utils/           # Utility e helper functions
│   └── gui/             # Interfaccia grafica (futuro)
├── data/                # File CSV con articoli
├── config/              # File di configurazione
├── tests/               # Test unitari
└── main.py              # Entry point dell'applicazione
```

## Installazione

### Opzione 1: Docker (Raccomandato)

1. Assicurati di avere Docker installato
2. Build dell'immagine:
   ```bash
   docker build -t nerdnostalgia:latest .
   # oppure
   docker-compose build
   ```
3. Configura l'applicazione (vedi sezione Configurazione)
4. Usa lo script helper per eseguire i comandi:
   ```bash
   ./docker-run.sh help
   ```

### Opzione 2: Installazione locale con Poetry (Raccomandato)

1. Clona il repository
2. Installa Poetry se non già installato:
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   # oppure
   make install-poetry
   ```
3. Installa le dipendenze:
   ```bash
   poetry install
   # oppure
   make install
   ```
4. Attiva l'ambiente virtuale:
   ```bash
   poetry shell
   ```

### Opzione 3: Installazione locale con pip

1. Clona il repository
2. Crea un ambiente virtuale:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Su Windows: venv\Scripts\activate
   ```
3. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```

## Configurazione

1. Copia il file di configurazione template:
   ```bash
   cp config/config.template.yaml config/config.yaml
   ```
2. Inserisci le tue credenziali eBay nel file `config/config.yaml`
   - Registrati su [eBay Developers](https://developer.ebay.com/)
   - Crea un'applicazione e ottieni App ID, Dev ID, Cert ID
   - Genera un User Token
3. (Opzionale) Copia `.env.example` in `.env` per usare variabili d'ambiente

## Utilizzo

### Con Docker

Usa lo script helper `docker-run.sh`:

```bash
# Pubblica articoli (dry-run per test)
./docker-run.sh publish --csv data/example.csv --dry-run

# Pubblica realmente su eBay
./docker-run.sh publish --csv data/example.csv --platform ebay

# Recupera categorie eBay
./docker-run.sh categories --platform ebay

# Crea un nuovo template CSV
./docker-run.sh init-csv data/my_items.csv

# Shell interattiva nel container
./docker-run.sh shell

# Esegui test
./docker-run.sh test
```

Oppure usa docker-compose:

```bash
# Esegui un comando
docker-compose run --rm nerdnostalgia publish --csv data/example.csv --dry-run

# Modalità sviluppo
docker-compose --profile dev run --rm nerdnostalgia-dev --help
```

### Senza Docker (con Poetry)

```bash
# Pubblica articoli
poetry run python main.py publish --csv data/example.csv --platform ebay

# Dry-run (simula senza pubblicare)
poetry run python main.py publish --csv data/example.csv --dry-run

# Recupera categorie
poetry run python main.py categories --platform ebay

# Oppure usa il Makefile
make publish
make categories

# Altri comandi
poetry run python main.py --help
```

### Senza Docker (con pip)

```bash
# Attiva l'ambiente virtuale prima
source venv/bin/activate

# Pubblica articoli
python main.py publish --csv data/example.csv --platform ebay

# Altri comandi
python main.py --help
```

## Formato CSV

Il file CSV deve contenere le seguenti colonne:
- `title`: Titolo dell'articolo
- `description`: Descrizione dettagliata
- `price`: Prezzo
- `quantity`: Quantità disponibile
- `category`: Categoria del prodotto
- `condition`: Condizione (new, used, refurbished)
- `images`: Path alle immagini (separati da ;)

Vedi `data/template.csv` per un esempio.

## Poetry

NerdNostalgia usa **Poetry** per la gestione delle dipendenze, che offre:
- Risoluzione delle dipendenze più veloce e affidabile
- Lock file per build riproducibili
- Gestione semplificata di pacchetti e dipendenze dev
- Supporto per gruppi di dipendenze opzionali

### Comandi Poetry Utili

```bash
# Aggiungi una dipendenza
poetry add requests

# Aggiungi dipendenza di sviluppo
poetry add --group dev pytest

# Rimuovi dipendenza
poetry remove requests

# Aggiorna dipendenze
poetry update

# Mostra dipendenze installate
poetry show --tree

# Esporta requirements.txt (per compatibilità)
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

## Docker

### Caratteristiche

- **Multi-stage build**: Immagine ottimizzata e leggera con Poetry
- **Python 3.13**: Ultima versione di Python
- **Poetry**: Gestione dipendenze moderna e affidabile
- **Volumi persistenti**: Dati, config e log montati dall'host
- **Utente non-root**: Maggiore sicurezza
- **Script helper**: Facile utilizzo con `docker-run.sh`
- **Healthcheck**: Monitoring automatico del container

### Build e Test

```bash
# Build dell'immagine
./docker-run.sh build

# Test rapido con dry-run
./docker-run.sh publish --csv data/example.csv --dry-run

# Verifica che tutto funzioni
./docker-run.sh shell
```

### Gestione Volumi

I seguenti volumi sono montati automaticamente:
- `./data` → `/app/data` - File CSV con articoli
- `./config` → `/app/config` - File di configurazione
- `./logs` → `/app/logs` - Log dell'applicazione

### Docker Compose

```bash
# Build
docker-compose build

# Esegui comando
docker-compose run --rm nerdnostalgia [COMANDO]

# Modalità sviluppo (con hot-reload)
docker-compose --profile dev up nerdnostalgia-dev
```

### Troubleshooting

Se hai problemi di permessi sui volumi:
```bash
# Assicurati che le directory esistano e siano scrivibili
mkdir -p data config logs
chmod 755 data config logs
```

Per vedere i log in real-time:
```bash
tail -f logs/nerdnostalgia.log
```

## Roadmap

- [x] Struttura base del progetto
- [x] Parser CSV completo
- [x] Integrazione eBay API
- [x] Docker support con Python 3.13
- [ ] Gestione immagini e upload
- [ ] Supporto per altre piattaforme (Amazon, Subito.it, etc.)
- [ ] Database per tracking listing
- [ ] Interfaccia grafica (GUI)
- [ ] Sistema di acquisto diretto
- [ ] API REST per integrazione esterna

## Licenza

TBD
