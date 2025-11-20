# Multi-stage build per ottimizzare le dimensioni dell'immagine con Poetry
FROM python:3.13-slim as builder

# Metadata
LABEL maintainer="your.email@example.com"
LABEL description="NerdNostalgia - Sistema di gestione articoli per e-commerce"

# Imposta variabili d'ambiente per Python e Poetry
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Poetry settings
    POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Aggiungi Poetry al PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Installa dipendenze di sistema necessarie per build
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Installa Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    chmod +x $POETRY_HOME/bin/poetry

# Verifica installazione Poetry
RUN poetry --version

# Crea directory di lavoro
WORKDIR /app

# Copia solo i file di configurazione Poetry per sfruttare la cache Docker
COPY pyproject.toml poetry.lock* ./

# Installa dipendenze (solo production, non dev)
# --no-root: non installa il pacchetto stesso, solo le dipendenze
# --no-directory: evita errori se mancano file del progetto
RUN poetry install --only main --no-root --no-directory && \
    rm -rf $POETRY_CACHE_DIR

# Stage finale - immagine più leggera
FROM python:3.13-slim

# Metadata per stage finale
LABEL maintainer="your.email@example.com"
LABEL description="NerdNostalgia - Sistema di gestione articoli per e-commerce"
LABEL version="0.1.0"

# Imposta variabili d'ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Disabilita creazione di virtualenv (non necessario in container)
    POETRY_VIRTUALENVS_CREATE=false \
    # Path Python
    PYTHONPATH=/app:$PYTHONPATH

# Installa solo le dipendenze runtime minime (se necessarie)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     libgomp1 \
#     && rm -rf /var/lib/apt/lists/*

# Crea utente non-root per sicurezza
RUN useradd -m -u 1000 nerduser && \
    mkdir -p /app /app/data /app/config /app/logs && \
    chown -R nerduser:nerduser /app

# Imposta directory di lavoro
WORKDIR /app

# Copia le dipendenze Python dallo stage builder
# Poetry installa i pacchetti nel site-packages globale
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copia il codice dell'applicazione
COPY --chown=nerduser:nerduser . .

# Crea le directory necessarie con permessi corretti
RUN mkdir -p data config logs && \
    chown -R nerduser:nerduser data config logs

# Rendi main.py eseguibile
RUN chmod +x main.py

# Passa all'utente non-root
USER nerduser

# Volume per dati persistenti
VOLUME ["/app/data", "/app/config", "/app/logs"]

# Healthcheck (opzionale - utile per orchestrazione)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Entry point
ENTRYPOINT ["python", "main.py"]

# Default command (mostra help)
CMD ["--help"]
