#!/bin/bash
# Script helper per eseguire NerdNostalgia con Docker

set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funzioni helper
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Verifica che Docker sia installato
if ! command -v docker &> /dev/null; then
    error "Docker non è installato. Installalo da https://docker.com"
fi

# Verifica che docker-compose sia installato (opzionale)
if ! command -v docker-compose &> /dev/null; then
    warn "docker-compose non trovato, verrà usato 'docker compose'"
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Funzione per build dell'immagine
build_image() {
    info "Building Docker image..."
    docker build -t nerdnostalgia:latest .
    info "Build completato!"
}

# Funzione per eseguire un comando
run_command() {
    docker run --rm \
        -v "$(pwd)/data:/app/data" \
        -v "$(pwd)/config:/app/config" \
        -v "$(pwd)/logs:/app/logs" \
        nerdnostalgia:latest "$@"
}

# Parsing argomenti
case "${1:-help}" in
    build)
        build_image
        ;;

    publish)
        shift
        info "Pubblicazione articoli..."
        run_command publish "$@"
        ;;

    categories)
        shift
        info "Recupero categorie..."
        run_command categories "$@"
        ;;

    init-csv)
        shift
        info "Creazione template CSV..."
        run_command init-csv "$@"
        ;;

    get-item)
        shift
        info "Recupero dettagli articolo..."
        run_command get-item "$@"
        ;;

    shell)
        info "Avvio shell interattiva..."
        docker run --rm -it \
            -v "$(pwd)/data:/app/data" \
            -v "$(pwd)/config:/app/config" \
            -v "$(pwd)/logs:/app/logs" \
            --entrypoint /bin/bash \
            nerdnostalgia:latest
        ;;

    test)
        info "Esecuzione test..."
        docker run --rm \
            -v "$(pwd):/app" \
            nerdnostalgia:latest \
            pytest tests/ -v
        ;;

    clean)
        info "Rimozione container e immagini..."
        docker rm -f nerdnostalgia 2>/dev/null || true
        docker rmi nerdnostalgia:latest 2>/dev/null || true
        info "Pulizia completata"
        ;;

    help|--help|-h)
        cat << EOF
${GREEN}NerdNostalgia Docker Helper${NC}

Uso: ./docker-run.sh [COMANDO] [OPZIONI]

Comandi disponibili:
  ${YELLOW}build${NC}                  Build dell'immagine Docker
  ${YELLOW}publish${NC} [opzioni]      Pubblica articoli da CSV
  ${YELLOW}categories${NC} [opzioni]   Recupera categorie piattaforma
  ${YELLOW}init-csv${NC} [path]        Crea template CSV
  ${YELLOW}get-item${NC} [opzioni]     Recupera dettagli articolo
  ${YELLOW}shell${NC}                  Apri shell interattiva nel container
  ${YELLOW}test${NC}                   Esegui test
  ${YELLOW}clean${NC}                  Rimuovi container e immagini
  ${YELLOW}help${NC}                   Mostra questo messaggio

Esempi:
  ${GREEN}# Build dell'immagine${NC}
  ./docker-run.sh build

  ${GREEN}# Pubblica articoli (dry-run)${NC}
  ./docker-run.sh publish --csv data/example.csv --dry-run

  ${GREEN}# Pubblica su eBay${NC}
  ./docker-run.sh publish --csv data/my_items.csv --platform ebay

  ${GREEN}# Recupera categorie${NC}
  ./docker-run.sh categories --platform ebay

  ${GREEN}# Shell interattiva${NC}
  ./docker-run.sh shell

Nota: Assicurati di aver configurato config/config.yaml prima dell'uso!
EOF
        ;;

    *)
        error "Comando sconosciuto: $1. Usa './docker-run.sh help' per la lista dei comandi."
        ;;
esac
