.PHONY: help build run shell test clean publish categories init-csv docker-build docker-clean install dev

# Variabili
DOCKER_IMAGE = nerdnostalgia
DOCKER_TAG = latest
PYTHON = python3
POETRY = poetry

# Colori per output
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[1;33m
NC = \033[0m # No Color

help: ## Mostra questo messaggio di aiuto
	@echo "$(GREEN)NerdNostalgia - Makefile$(NC)"
	@echo ""
	@echo "Comandi disponibili:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Docker:$(NC)"
	@echo "  $(YELLOW)make docker-build$(NC)     Build immagine Docker"
	@echo "  $(YELLOW)make docker-run$(NC)       Esegui con Docker"
	@echo "  $(YELLOW)make docker-shell$(NC)     Shell Docker interattiva"
	@echo ""
	@echo "$(GREEN)Local:$(NC)"
	@echo "  $(YELLOW)make install$(NC)          Installa dipendenze localmente"
	@echo "  $(YELLOW)make test$(NC)             Esegui test localmente"
	@echo "  $(YELLOW)make run$(NC)              Esegui localmente"

# Setup e installazione
install-poetry: ## Installa Poetry se non presente
	@if ! command -v poetry &> /dev/null; then \
		echo "$(YELLOW)Poetry non trovato. Installazione...$(NC)"; \
		curl -sSL https://install.python-poetry.org | python3 -; \
		echo "$(GREEN)✓ Poetry installato! Riavvia il terminale o esegui: source ~/.bashrc$(NC)"; \
	else \
		echo "$(GREEN)✓ Poetry già installato ($(shell poetry --version))$(NC)"; \
	fi

install: install-poetry ## Installa dipendenze Python con Poetry
	@echo "$(GREEN)Installazione dipendenze con Poetry...$(NC)"
	$(POETRY) install --only main
	@echo "$(GREEN)✓ Installazione completata!$(NC)"

install-dev: install-poetry ## Installa dipendenze di sviluppo con Poetry
	@echo "$(GREEN)Installazione dipendenze di sviluppo con Poetry...$(NC)"
	$(POETRY) install --with dev
	@echo "$(GREEN)✓ Installazione dev completata!$(NC)"

install-all: install-poetry ## Installa tutte le dipendenze (main + dev)
	@echo "$(GREEN)Installazione completa con Poetry...$(NC)"
	$(POETRY) install
	@echo "$(GREEN)✓ Installazione completa!$(NC)"

poetry-lock: ## Aggiorna poetry.lock
	@echo "$(GREEN)Aggiornamento poetry.lock...$(NC)"
	$(POETRY) lock --no-update
	@echo "$(GREEN)✓ Lock file aggiornato!$(NC)"

poetry-update: ## Aggiorna tutte le dipendenze
	@echo "$(YELLOW)Aggiornamento dipendenze...$(NC)"
	$(POETRY) update
	@echo "$(GREEN)✓ Dipendenze aggiornate!$(NC)"

poetry-show: ## Mostra dipendenze installate
	@$(POETRY) show --tree

config: ## Crea file di configurazione da template
	@if [ ! -f config/config.yaml ]; then \
		echo "$(YELLOW)Creazione config.yaml da template...$(NC)"; \
		cp config/config.template.yaml config/config.yaml; \
		echo "$(GREEN)✓ Config creato! Modifica config/config.yaml con le tue credenziali.$(NC)"; \
	else \
		echo "$(YELLOW)config.yaml già esistente, nessuna modifica effettuata.$(NC)"; \
	fi

# Docker
docker-build: ## Build immagine Docker
	@echo "$(GREEN)Building Docker image...$(NC)"
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .
	@echo "$(GREEN)✓ Build completato!$(NC)"

docker-run: ## Esegui con Docker (esempio)
	@echo "$(GREEN)Esecuzione con Docker...$(NC)"
	docker run --rm \
		-v "$$(pwd)/data:/app/data" \
		-v "$$(pwd)/config:/app/config" \
		-v "$$(pwd)/logs:/app/logs" \
		$(DOCKER_IMAGE):$(DOCKER_TAG) --help

docker-shell: ## Apri shell interattiva Docker
	@echo "$(GREEN)Apertura shell Docker...$(NC)"
	docker run --rm -it \
		-v "$$(pwd)/data:/app/data" \
		-v "$$(pwd)/config:/app/config" \
		-v "$$(pwd)/logs:/app/logs" \
		--entrypoint /bin/bash \
		$(DOCKER_IMAGE):$(DOCKER_TAG)

docker-test: ## Esegui test in Docker
	@echo "$(GREEN)Esecuzione test in Docker...$(NC)"
	docker run --rm \
		-v "$$(pwd):/app" \
		$(DOCKER_IMAGE):$(DOCKER_TAG) \
		python -m pytest tests/ -v

docker-publish-dry: ## Test pubblicazione (dry-run) con Docker
	@echo "$(GREEN)Test pubblicazione (dry-run)...$(NC)"
	docker run --rm \
		-v "$$(pwd)/data:/app/data" \
		-v "$$(pwd)/config:/app/config" \
		-v "$$(pwd)/logs:/app/logs" \
		$(DOCKER_IMAGE):$(DOCKER_TAG) publish --csv data/example.csv --dry-run

docker-compose-build: ## Build con docker-compose
	docker-compose build

docker-compose-up: ## Avvia con docker-compose
	docker-compose up -d

docker-compose-down: ## Ferma docker-compose
	docker-compose down

docker-clean: ## Rimuovi immagini e container Docker
	@echo "$(RED)Pulizia Docker...$(NC)"
	docker rm -f nerdnostalgia 2>/dev/null || true
	docker rmi $(DOCKER_IMAGE):$(DOCKER_TAG) 2>/dev/null || true
	@echo "$(GREEN)✓ Pulizia completata!$(NC)"

# Esecuzione locale
run: ## Esegui applicazione localmente (mostra help)
	@$(POETRY) run python main.py --help

publish: ## Pubblica articoli da CSV (esempio con dry-run)
	@$(POETRY) run python main.py publish --csv data/example.csv --dry-run

categories: ## Recupera categorie eBay
	@$(POETRY) run python main.py categories --platform ebay

init-csv: ## Crea template CSV
	@$(POETRY) run python main.py init-csv data/my_items.csv

shell: ## Apri shell Python con ambiente Poetry
	@$(POETRY) shell

# Testing e QA
test: ## Esegui test unitari
	@echo "$(GREEN)Esecuzione test...$(NC)"
	$(POETRY) run pytest tests/ -v

test-cov: ## Esegui test con coverage
	@echo "$(GREEN)Esecuzione test con coverage...$(NC)"
	$(POETRY) run pytest --cov=src --cov-report=html --cov-report=term tests/
	@echo "$(GREEN)✓ Report salvato in htmlcov/index.html$(NC)"

lint: ## Esegui linting con flake8
	@echo "$(GREEN)Linting...$(NC)"
	$(POETRY) run flake8 src/ tests/ --max-line-length=100 --exclude=__pycache__

format: ## Formatta codice con black
	@echo "$(GREEN)Formattazione codice...$(NC)"
	$(POETRY) run black src/ tests/ main.py

format-check: ## Verifica formattazione senza modificare
	@echo "$(GREEN)Verifica formattazione...$(NC)"
	$(POETRY) run black --check src/ tests/ main.py

type-check: ## Type checking con mypy
	@echo "$(GREEN)Type checking...$(NC)"
	$(POETRY) run mypy src/ --ignore-missing-imports

qa: lint format-check type-check test ## Esegui tutti i check di qualità

# Utility
clean: ## Pulisci file temporanei
	@echo "$(RED)Pulizia file temporanei...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache htmlcov .coverage .mypy_cache
	@echo "$(GREEN)✓ Pulizia completata!$(NC)"

clean-all: clean docker-clean ## Pulizia completa (include Docker)

logs: ## Mostra ultimi log
	@if [ -f logs/nerdnostalgia.log ]; then \
		tail -f logs/nerdnostalgia.log; \
	else \
		echo "$(YELLOW)Nessun file di log trovato$(NC)"; \
	fi

setup: install-poetry config install ## Setup completo (Poetry + config + install)
	@echo "$(GREEN)Setup completato! Ora configura config/config.yaml con le tue credenziali.$(NC)"

setup-dev: install-poetry config install-dev ## Setup completo per sviluppo
	@echo "$(GREEN)Setup sviluppo completato!$(NC)"

# Quick start
quickstart: docker-build docker-publish-dry ## Quick start completo con Docker
	@echo ""
	@echo "$(GREEN)╔════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║   NerdNostalgia Quick Start OK!       ║$(NC)"
	@echo "$(GREEN)╚════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "Prossimi passi:"
	@echo "  1. Configura: $(YELLOW)config/config.yaml$(NC)"
	@echo "  2. Testa:     $(YELLOW)make docker-publish-dry$(NC)"
	@echo "  3. Pubblica:  $(YELLOW)./docker-run.sh publish --csv data/example.csv$(NC)"
	@echo ""

# Default target
.DEFAULT_GOAL := help
