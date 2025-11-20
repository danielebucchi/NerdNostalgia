# Guida Docker per NerdNostalgia

Documentazione dettagliata per l'uso di NerdNostalgia con Docker.

## Requisiti

- Docker >= 20.10
- Docker Compose >= 2.0 (opzionale ma raccomandato)

## Quick Start

```bash
# 1. Build dell'immagine
./docker-run.sh build

# 2. Configura le credenziali
cp config/config.template.yaml config/config.yaml
# Modifica config/config.yaml con le tue credenziali eBay

# 3. Test con dry-run
./docker-run.sh publish --csv data/example.csv --dry-run

# 4. Pubblica realmente
./docker-run.sh publish --csv data/example.csv --platform ebay
```

## Architettura Docker

### Multi-stage Build

Il Dockerfile utilizza un approccio multi-stage per ottimizzare:

1. **Stage Builder**: Compila e installa le dipendenze Python
2. **Stage Finale**: Copia solo i file necessari per un'immagine leggera

Vantaggi:
- Immagine finale più piccola (~150MB vs ~300MB)
- Nessun tool di build nell'immagine finale
- Maggiore sicurezza

### Sicurezza

- **Utente non-root**: L'applicazione gira come `nerduser` (UID 1000)
- **Read-only filesystem**: Possibile con volumi esterni
- **No secrets nell'immagine**: Config montato come volume

## Uso Dettagliato

### Script Helper (docker-run.sh)

Lo script `docker-run.sh` semplifica l'uso di Docker:

```bash
# Mostra tutti i comandi disponibili
./docker-run.sh help

# Build
./docker-run.sh build

# Pubblica articoli
./docker-run.sh publish --csv data/my_items.csv --platform ebay

# Dry-run (test senza pubblicare)
./docker-run.sh publish --csv data/my_items.csv --dry-run

# Recupera categorie
./docker-run.sh categories --platform ebay --output data/categories.json

# Inizializza un CSV vuoto
./docker-run.sh init-csv data/new_items.csv

# Recupera dettagli articolo
./docker-run.sh get-item --item-id 123456789 --platform ebay

# Shell interattiva
./docker-run.sh shell

# Esegui test
./docker-run.sh test

# Pulizia
./docker-run.sh clean
```

### Docker Compose

Per usi più avanzati:

```bash
# Build
docker-compose build

# Esegui comando singolo
docker-compose run --rm nerdnostalgia publish --csv data/example.csv --dry-run

# Modalità sviluppo (monta il codice sorgente)
docker-compose --profile dev run --rm nerdnostalgia-dev

# Background service (per futuro web UI)
docker-compose up -d nerdnostalgia

# Logs
docker-compose logs -f nerdnostalgia

# Stop
docker-compose down
```

### Comandi Docker Raw

Se preferisci usare Docker direttamente:

```bash
# Build
docker build -t nerdnostalgia:latest .

# Run con volumi
docker run --rm \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/config:/app/config" \
  -v "$(pwd)/logs:/app/logs" \
  nerdnostalgia:latest publish --csv data/example.csv --dry-run

# Shell interattiva
docker run --rm -it \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/config:/app/config" \
  -v "$(pwd)/logs:/app/logs" \
  --entrypoint /bin/bash \
  nerdnostalgia:latest

# Esegui test
docker run --rm \
  -v "$(pwd):/app" \
  nerdnostalgia:latest \
  python -m pytest tests/ -v
```

## Gestione Volumi

### Volumi Host (Default)

Il setup di default monta directory dall'host:

```yaml
volumes:
  - ./data:/app/data       # CSV files
  - ./config:/app/config   # Configuration
  - ./logs:/app/logs       # Application logs
```

**Pro**: Facile accesso ai file dall'host
**Contro**: Possibili problemi di permessi su alcuni sistemi

### Named Volumes (Alternativa)

Per dati completamente gestiti da Docker:

```yaml
volumes:
  - nerdnostalgia_data:/app/data
  - nerdnostalgia_config:/app/config
  - nerdnostalgia_logs:/app/logs

volumes:
  nerdnostalgia_data:
  nerdnostalgia_config:
  nerdnostalgia_logs:
```

**Pro**: Nessun problema di permessi
**Contro**: Più difficile accedere ai file

#### Gestire Named Volumes

```bash
# Lista volumi
docker volume ls | grep nerdnostalgia

# Ispeziona volume
docker volume inspect nerdnostalgia_data

# Backup di un volume
docker run --rm \
  -v nerdnostalgia_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/data-backup.tar.gz -C /data .

# Restore di un volume
docker run --rm \
  -v nerdnostalgia_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/data-backup.tar.gz -C /data

# Rimuovi volumi
docker-compose down -v
```

## Sviluppo con Docker

### Hot Reload

Il profilo `dev` monta il codice sorgente:

```bash
# Avvia in modalità sviluppo
docker-compose --profile dev run --rm nerdnostalgia-dev

# Modifica il codice sull'host, le modifiche sono visibili nel container
```

### Debug

```bash
# Shell con ambiente configurato
./docker-run.sh shell

# All'interno del container:
python -m pdb main.py publish --csv data/example.csv --dry-run

# Oppure aggiungi breakpoint nel codice:
import pdb; pdb.set_trace()
```

### Test

```bash
# Esegui tutti i test
./docker-run.sh test

# Test specifico
docker run --rm \
  -v "$(pwd):/app" \
  nerdnostalgia:latest \
  python -m pytest tests/test_parser.py -v

# Test con coverage
docker run --rm \
  -v "$(pwd):/app" \
  nerdnostalgia:latest \
  python -m pytest --cov=src tests/ -v
```

## Troubleshooting

### Problemi di Permessi

Se vedi errori tipo "Permission denied":

```bash
# Soluzione 1: Assicurati che le directory siano scrivibili
mkdir -p data config logs
chmod -R 755 data config logs

# Soluzione 2: Usa l'UID del tuo utente
docker run --rm \
  --user $(id -u):$(id -g) \
  -v "$(pwd)/data:/app/data" \
  nerdnostalgia:latest publish --csv data/example.csv --dry-run

# Soluzione 3: Usa named volumes invece di bind mounts
```

### Build Lenta

```bash
# Usa BuildKit per build più veloci
DOCKER_BUILDKIT=1 docker build -t nerdnostalgia:latest .

# Cache layers per build incrementali
# (già abilitato nel Dockerfile)
```

### Immagine Troppo Grande

```bash
# Verifica dimensione
docker images nerdnostalgia

# Analizza layer
docker history nerdnostalgia:latest

# Pulisci cache build
docker builder prune -a

# L'immagine dovrebbe essere ~150-200MB
```

### Container Non Si Avvia

```bash
# Verifica logs
docker logs nerdnostalgia

# Controlla che config.yaml esista
ls -la config/config.yaml

# Test minimo
docker run --rm nerdnostalgia:latest --help
```

## Best Practices

### Produzione

```dockerfile
# Usa tag specifici, non :latest
nerdnostalgia:0.1.0

# Health check (per futuro web UI)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

# Limita risorse
docker run --memory="512m" --cpus="1.0" nerdnostalgia:latest

# Logs strutturati
docker run --log-driver json-file --log-opt max-size=10m nerdnostalgia:latest
```

### CI/CD

```yaml
# GitHub Actions example
- name: Build Docker image
  run: docker build -t nerdnostalgia:${{ github.sha }} .

- name: Test
  run: docker run --rm nerdnostalgia:${{ github.sha }} python -m pytest

- name: Push to registry
  run: |
    docker tag nerdnostalgia:${{ github.sha }} registry.io/nerdnostalgia:latest
    docker push registry.io/nerdnostalgia:latest
```

### Sicurezza

```bash
# Scansiona vulnerabilità
docker scan nerdnostalgia:latest

# Non includere secrets nell'immagine
# Usa variabili d'ambiente o volumi
docker run --rm \
  --env-file .env \
  -v "$(pwd)/config:/app/config:ro" \
  nerdnostalgia:latest

# Usa immagini ufficiali
FROM python:3.13-slim  # ✓ Ufficiale e mantenuta
```

## Registry e Deploy

### Push a Docker Hub

```bash
# Tag
docker tag nerdnostalgia:latest yourusername/nerdnostalgia:latest

# Login
docker login

# Push
docker push yourusername/nerdnostalgia:latest

# Pull su altro sistema
docker pull yourusername/nerdnostalgia:latest
```

### Deploy su Server

```bash
# Su server remoto via SSH
ssh user@server "docker pull yourusername/nerdnostalgia:latest"

# Con docker-compose
scp docker-compose.yml user@server:/app/
ssh user@server "cd /app && docker-compose up -d"

# Con Kubernetes (futuro)
kubectl apply -f k8s/deployment.yaml
```

## Riferimenti

- [Dockerfile](./Dockerfile)
- [docker-compose.yml](./docker-compose.yml)
- [docker-run.sh](./docker-run.sh)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
