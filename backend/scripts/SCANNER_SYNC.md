# Scanner carte: la cartella dello scanner, una volta al giorno

`scanner_sync.py` confronta la cartella dove lo scanner salva le carte con
quella del giro precedente e manda allo Scanner carte solo i file nuovi o
cambiati. Le carte riconosciute con certezza vanno in collezione da sole; le
altre aspettano in **admin → Scanner carte → Da confermare**.

```
cartella dello scanner ──► scanner_sync.py (1 volta al giorno) ──► /api/card-scanner
  file nuovi/cambiati          stato: impronte dei file gia' caricati      ├─ sicure → collezione
                                                                             └─ le altre → da confermare
```

- La cartella **non viene toccata**: niente spostamenti, niente cancellazioni.
- Lo stato è l'impronta (SHA-1) del contenuto: un file **rinominato o spostato**
  non si ricarica, uno **modificato** sì.
- Un file che non si riesce a caricare (server spento, rete giù) non entra nello
  stato: si riprova da solo al giro dopo.
- I file scritti da meno di 30 secondi si saltano (lo scanner potrebbe non aver
  finito) e si prendono al giro dopo.

Diverso da `scanner_watch.py`, che resta acceso, carica appena il file compare e
lo sposta in `caricati/`.

## Come organizzare la cartella

- **Gioco**: dal nome di una cartella nel percorso — `Pokemon`, `Magic`,
  `YuGiOh`, `OnePiece`, a qualsiasi livello (`Carte\Pokemon\2026-11\carta01.jpg`).
  Altrimenti quello scritto nella configurazione, altrimenti quello scelto nella
  pagina Scanner carte.
- **Retro** (facoltativo, migliora la stima della condizione): stesso nome del
  fronte più `_retro` → `carta12.jpg` + `carta12_retro.jpg`.
- Formati: JPEG, PNG, TIFF, BMP, WebP. 300–600 dpi.

## Installazione su Windows (dal sito)

1. **admin → Scanner carte → Impostazioni → Scarica per Windows**: uno ZIP con
   tutto, e l'indirizzo del sito già scritto dentro (`predefiniti.ini`, mai
   password).
2. Estrai lo ZIP e fai doppio clic su **`Installa.cmd`**. Se Windows dice "PC
   protetto": *Ulteriori informazioni → Esegui comunque* (il file non è firmato).
3. L'installazione guidata (`windows/Installa.ps1`):
   Python con winget se manca, Pillow, copia in
   `%LOCALAPPDATA%\NerdNostalgia\Scanner`, scelta della cartella con la finestra
   di Windows, utente e password, cosa fare dei file **già** nella cartella
   (caricarli o ignorarli e partire da oggi), ora del giro giornaliero, icona
   **"Carica carte adesso"** sul desktop.

Per aggiornare o cambiare impostazioni si rilancia `Installa.cmd`; per togliere
tutto `Disinstalla.cmd` (la configurazione e lo stato si tengono, se non si dice
di cancellarli).

## Installazione su Windows (a mano)

1. **Python** da <https://www.python.org/downloads/> (non quello del Microsoft
   Store), spuntando *Add python.exe to PATH*.
2. **Pillow**, per ridurre gli scan grossi e leggere i TIFF. Da PowerShell:
   ```
   python -m pip install pillow
   ```
3. Copia `scanner_sync.py` e `installa-scanner-sync.ps1` in una cartella, ad
   esempio `C:\NerdNostalgia`.
4. **Configurazione** (cartella dello scanner, sito, utente e password admin):
   ```
   cd C:\NerdNostalgia
   python scanner_sync.py --configura
   ```
   Finisce in `%APPDATA%\NerdNostalgia\scanner_sync.ini`, insieme allo stato e
   al log. Contiene la password: non metterla in una cartella condivisa.
5. **Prova** senza caricare niente, poi un giro vero:
   ```
   python scanner_sync.py --prova
   python scanner_sync.py
   ```
6. **Pianificazione** giornaliera (ogni giorno alle 21:00, o `-Ora 08:30`):
   ```
   powershell -ExecutionPolicy Bypass -File .\installa-scanner-sync.ps1
   ```
   Se a quell'ora il PC è spento, il giro parte alla riaccensione. Gira con il
   tuo utente, senza finestre. Per provarlo subito:
   `Start-ScheduledTask -TaskName "NerdNostalgia - Scanner carte"`.
   Per toglierlo: `.\installa-scanner-sync.ps1 -Rimuovi`.

## Controllare cosa è successo

Il log è in `%APPDATA%\NerdNostalgia\scanner_sync.log` (su Mac
`~/.config/nerdnostalgia/`). Ogni giro finisce con una riga così:

```
Fatto: 12 caricati, 9 in collezione, 3 da confermare nella pagina, 0 errori
```

Per ricaricare tutto da capo (ad esempio dopo aver cancellato le carte dal
sito) si cancella il file `stato-*.json` nella stessa cartella.

## Opzioni della configurazione

| Chiave | Default | Cosa fa |
|---|---|---|
| `cartella` | — | Dove lo scanner salva le carte (anche sottocartelle) |
| `api` | `https://api.nerdnostalgia.store` | Indirizzo del backend |
| `utente` / `password` | — | Un utente admin del sito |
| `gioco` | vuoto | Gioco se la cartella non lo dice; vuoto = quello della pagina |
| `auto_conferma` | `si` | Mette in collezione da sole le carte sicure |
| `valuta_subito` | `si` | Le valuta subito (CardTrader + eBay) |
