# Sync Vinted "da locale" (Mac → prod)

Vinted/Cloudflare blocca Playwright headless quando gira da IP datacenter
(Hetzner, Contabo, OVH, AWS). Lo workaround pragmatico per single-user è
fare il **fetch dal tuo Mac** (IP residenziale, CF passa) e **pushare** gli
items via API al server.

Pipeline:

```
   Mac (residenziale)                Server (prod)
   ─────────────────                ─────────────────
   launchd / cron daily
        │
        ▼
   sync_from_local.py
   ├─ Playwright headless
   ├─ requests login → JWT
   └─ POST /api/vinted/import ───►  /api/vinted/import
                                    ├─ require_admin
                                    └─ persist_items() → DB + log
```

## Setup una tantum

### 1. Crea il venv dedicato al sync sul Mac

```bash
cd ~/PycharmProjects/Personali/nerdnostalgia
python3 -m venv backend/.venv-sync
backend/.venv-sync/bin/pip install --upgrade pip
backend/.venv-sync/bin/pip install -r backend/src/requirements.txt
backend/.venv-sync/bin/python -m playwright install chromium
```

### 2. File env con le credenziali

```bash
mkdir -p ~/.config/nerdnostalgia
cat > ~/.config/nerdnostalgia/sync.env <<'EOF'
NERDNOSTALGIA_API_URL=https://api.nerdnostalgia.store
NERDNOSTALGIA_USERNAME=admin
NERDNOSTALGIA_PASSWORD=la-tua-pwd-admin
VINTED_USER_ID=95521831
LOG_LEVEL=INFO
EOF
chmod 600 ~/.config/nerdnostalgia/sync.env
```

### 3. Test manuale (DRY RUN)

```bash
set -a; source ~/.config/nerdnostalgia/sync.env; set +a
DRY_RUN=1 backend/.venv-sync/bin/python backend/scripts/sync_from_local.py
```

Dovresti vedere il JSON degli items fetchati senza che venga pushato nulla.
Se invece vedi `VintedClientError: Nessuna risposta API intercettata`, anche
dal Mac CF ti blocca: prova di nuovo dopo qualche minuto o controlla che
Chromium non sia stato bannato (in tal caso, riapri Vinted nel tuo Chrome
normale e ri-prova — spesso CF "ricalibra" dopo una visita reale).

Test reale (push, una volta sola):
```bash
backend/.venv-sync/bin/python backend/scripts/sync_from_local.py
```

## Schedulazione daily (launchd)

`~/Library/LaunchAgents/com.nerdnostalgia.sync.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.nerdnostalgia.sync</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>set -a; source $HOME/.config/nerdnostalgia/sync.env; set +a; exec $HOME/PycharmProjects/Personali/nerdnostalgia/backend/.venv-sync/bin/python $HOME/PycharmProjects/Personali/nerdnostalgia/backend/scripts/sync_from_local.py</string>
    </array>

    <!-- Ogni giorno alle 09:00 (modifica Hour/Minute a piacere) -->
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>9</integer>
        <key>Minute</key><integer>0</integer>
    </dict>

    <key>RunAtLoad</key><false/>
    <key>StandardOutPath</key><string>/tmp/nerdnostalgia-sync.log</string>
    <key>StandardErrorPath</key><string>/tmp/nerdnostalgia-sync.log</string>
</dict>
</plist>
```

Caricalo:
```bash
launchctl load -w ~/Library/LaunchAgents/com.nerdnostalgia.sync.plist
launchctl list | grep nerdnostalgia       # verifica registrazione
```

Trigger manuale (test schedulazione):
```bash
launchctl start com.nerdnostalgia.sync
tail -f /tmp/nerdnostalgia-sync.log
```

Disabilitare:
```bash
launchctl unload -w ~/Library/LaunchAgents/com.nerdnostalgia.sync.plist
```

## Note operative

- **Mac in sleep**: launchd lancia il job al wake successivo se l'ora era
  passata mentre dormiva. Se vuoi fire-and-forget anche con Mac spento, usa
  `pmset` per svegliarlo poco prima dell'orario, oppure sposta il job su
  un device sempre acceso (RaspberryPi residenziale, vecchio Mac mini).
- **Notifica fallimento**: per ricevere un ping ntfy se il push fallisce,
  wrappa il comando con `|| curl -d "sync fallita" https://ntfy.nerdnostalgia.store/alerts`.
- **Logs server-side**: ogni run lascia traccia in `vinted_sync_logs`
  (tag `triggered_by="remote"`). Visibili da `/admin/import-vinted` o via
  `GET /api/vinted/logs`.
- **Sicurezza**: la pwd admin è in `~/.config/nerdnostalgia/sync.env` con
  `chmod 600`. Su Mac multi-utente, considera `keyring` Python con
  `security` di macOS al posto del file.
