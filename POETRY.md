# Guida Poetry per NerdNostalgia

Questa guida spiega come usare Poetry per gestire le dipendenze del progetto NerdNostalgia.

## Cos'è Poetry?

Poetry è un tool moderno per la gestione delle dipendenze e packaging in Python che:
- Risolve le dipendenze in modo deterministico
- Crea un file `poetry.lock` per build riproducibili
- Gestisce automaticamente i virtual environment
- Semplifica il publishing dei pacchetti
- Fornisce comandi intuitivi

## Installazione Poetry

### Linux / macOS / WSL

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Aggiungi Poetry al PATH (aggiungi al tuo `.bashrc` o `.zshrc`):
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Windows (PowerShell)

```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```

### Verifica Installazione

```bash
poetry --version
# Poetry (version 1.8.3)
```

### Con Make

```bash
make install-poetry
```

## Setup Progetto

### Prima Configurazione

```bash
# Installa tutte le dipendenze (main + dev)
poetry install

# Solo dipendenze main (produzione)
poetry install --only main

# Solo dipendenze dev
poetry install --only dev
```

### Attivare Virtual Environment

Poetry crea automaticamente un virtual environment. Per attivarlo:

```bash
# Metodo 1: Shell Poetry (raccomandato)
poetry shell

# Metodo 2: Run comando specifico
poetry run python main.py --help

# Metodo 3: Trova il path del venv
poetry env info --path
# Poi attivalo manualmente:
source $(poetry env info --path)/bin/activate
```

## Gestione Dipendenze

### Aggiungere Dipendenze

```bash
# Aggiungi dipendenza production
poetry add requests
poetry add "pandas>=2.0.0"

# Aggiungi dipendenza development
poetry add --group dev pytest
poetry add --group dev black mypy flake8

# Aggiungi dipendenza opzionale
poetry add --optional PyQt5
```

### Rimuovere Dipendenze

```bash
poetry remove requests
poetry remove --group dev pytest
```

### Aggiornare Dipendenze

```bash
# Aggiorna tutte le dipendenze
poetry update

# Aggiorna una specifica dipendenza
poetry update requests

# Aggiorna solo patch/minor (non major)
poetry update --lock
```

### Visualizzare Dipendenze

```bash
# Lista dipendenze
poetry show

# Albero delle dipendenze
poetry show --tree

# Dettagli di una dipendenza specifica
poetry show requests

# Solo outdated
poetry show --outdated
```

## File pyproject.toml

Il file `pyproject.toml` contiene tutta la configurazione del progetto:

```toml
[tool.poetry]
name = "nerdnostalgia"
version = "0.1.0"
description = "..."

[tool.poetry.dependencies]
python = "^3.11"
pandas = "^2.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
```

### Semantica delle Versioni

- `^2.0.0` - Permette >=2.0.0 <3.0.0 (raccomandato)
- `~2.0.0` - Permette >=2.0.0 <2.1.0
- `>=2.0.0` - Qualsiasi versione >= 2.0.0
- `2.0.0` - Esattamente 2.0.0

## File poetry.lock

Il file `poetry.lock`:
- Contiene le versioni esatte di tutte le dipendenze
- Garantisce build riproducibili
- Deve essere committato nel repository
- Si aggiorna con `poetry lock` o `poetry update`

```bash
# Rigenera lock senza aggiornare pacchetti
poetry lock --no-update

# Aggiorna lock e pacchetti
poetry update
```

## Comandi Utili

### Esecuzione

```bash
# Esegui comando nell'ambiente Poetry
poetry run python main.py

# Esegui script definito in pyproject.toml
poetry run nerdnostalgia --help

# Esegui pytest
poetry run pytest

# Esegui con Makefile
make test
make publish
```

### Virtual Environment

```bash
# Info ambiente
poetry env info

# Lista ambienti
poetry env list

# Rimuovi ambiente
poetry env remove python

# Usa Python specifico
poetry env use /usr/bin/python3.13
poetry env use python3.11
```

### Export

```bash
# Esporta requirements.txt (per compatibilità)
poetry export -f requirements.txt --output requirements.txt

# Senza hash (più leggibile)
poetry export -f requirements.txt --output requirements.txt --without-hashes

# Solo dev dependencies
poetry export --only dev -f requirements.txt --output requirements-dev.txt
```

### Build e Publish

```bash
# Build del package
poetry build

# Publish su PyPI (quando pronto)
poetry publish

# Build e publish insieme
poetry publish --build
```

## Integrazione con IDE

### VSCode

1. Installa l'estensione Python
2. Seleziona l'interprete Poetry:
   - `Cmd/Ctrl + Shift + P`
   - "Python: Select Interpreter"
   - Scegli quello che contiene `.venv` o usa il path da `poetry env info`

### PyCharm

PyCharm rileva automaticamente Poetry. Per configurare manualmente:
1. Settings → Project → Python Interpreter
2. Add Interpreter → Poetry Environment
3. Seleziona il path di Poetry

### Vim / Neovim

Usa plugin come `vim-poetry` o configura manualmente il path del venv.

## Workflow Tipico

### Sviluppo

```bash
# Setup iniziale
poetry install

# Attiva shell
poetry shell

# Lavora normalmente
python main.py --help
pytest

# Aggiungi nuova dipendenza
poetry add requests

# Fine sessione
exit  # o Ctrl+D
```

### CI/CD

```bash
# Install senza dev dependencies
poetry install --only main --no-interaction --no-ansi

# Run tests in CI
poetry run pytest

# Build
poetry build
```

### Docker

Il Dockerfile è già configurato per usare Poetry:
- Stage 1: Installa Poetry e dipendenze
- Stage 2: Copia solo i pacchetti necessari

## Troubleshooting

### Poetry non trovato

```bash
# Verifica installazione
which poetry

# Aggiungi al PATH
export PATH="$HOME/.local/bin:$PATH"

# Reinstalla
curl -sSL https://install.python-poetry.org | python3 - --uninstall
curl -sSL https://install.python-poetry.org | python3 -
```

### Problemi con Cache

```bash
# Pulisci cache Poetry
poetry cache clear pypi --all
poetry cache clear _default_cache --all

# Rimuovi virtualenv e reinstalla
poetry env remove python
poetry install
```

### Lock File Out of Date

```bash
# Rigenera lock file
poetry lock --no-update

# O aggiorna tutto
poetry update
```

### Conflitti di Dipendenze

```bash
# Mostra dettagli del conflitto
poetry add package_name --dry-run

# Forza versioni compatibili
poetry add "package_name>=1.0,<2.0"
```

## Migrazione da requirements.txt

Se hai già un `requirements.txt`:

```bash
# Importa da requirements.txt
cat requirements.txt | xargs poetry add

# Oppure manualmente
poetry add pandas pyyaml python-dotenv ebaysdk requests colorlog click
poetry add --group dev pytest pytest-cov black flake8 mypy
```

## Best Practices

1. **Committa sempre poetry.lock**: Garantisce build riproducibili
2. **Usa gruppi di dipendenze**: Separa dev, test, docs, etc.
3. **Versioni con ^**: Permette aggiornamenti minori sicuri
4. **Update regolari**: `poetry update` per security patches
5. **Export per CI legacy**: Se il CI non supporta Poetry
6. **Virtual env automatici**: Lascia che Poetry li gestisca

## Comandi Make

Abbiamo creato comandi make per semplificare l'uso:

```bash
make install-poetry    # Installa Poetry
make install          # Installa dipendenze
make install-dev      # Installa con dev dependencies
make poetry-lock      # Aggiorna lock file
make poetry-update    # Aggiorna dipendenze
make poetry-show      # Mostra dipendenze
make test            # Run test con Poetry
make format          # Format con black
make lint            # Lint con flake8
```

## Risorse

- [Documentazione Ufficiale Poetry](https://python-poetry.org/docs/)
- [Poetry su GitHub](https://github.com/python-poetry/poetry)
- [pyproject.toml Spec](https://peps.python.org/pep-0621/)
- [Semantic Versioning](https://semver.org/)

## FAQ

**Q: Poetry è lento?**
A: La prima volta è più lento per risolvere le dipendenze, ma poi è cached. Usa `--no-cache` se hai problemi.

**Q: Posso usare pip insieme a Poetry?**
A: Sconsigliato. Poetry gestisce tutto. Se necessario, usa `poetry run pip install`.

**Q: Come aggiorno Poetry stesso?**
A: `poetry self update`

**Q: Poetry crea sempre un venv?**
A: Sì, a meno che non sia già in un venv o usi `POETRY_VIRTUALENVS_CREATE=false`

**Q: Dove sono i venv di Poetry?**
A: Default: `~/.cache/pypoetry/virtualenvs/` oppure `poetry env info` per il path esatto
