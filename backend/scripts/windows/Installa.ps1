<#
  Installazione guidata dello Scanner carte di NerdNostalgia su Windows.

  Si lancia con doppio clic su Installa.cmd. Fa, in ordine:
    1. Python (con winget se manca) e Pillow
    2. copia dei file in %LOCALAPPDATA%\NerdNostalgia\Scanner
    3. scelta della cartella dello scanner (finestra di Windows)
    4. configurazione: utente e password admin
    5. cosa fare dei file gia' presenti nella cartella
    6. pianificazione giornaliera + icona "Carica carte adesso" sul desktop

  Si puo' rilanciare quando si vuole: aggiorna i file e la configurazione.
  NB: file in solo ASCII. PowerShell 5 legge gli script senza BOM come
  ANSI, e le lettere accentate diventerebbero caratteri strani.
#>
$ErrorActionPreference = "Stop"
$Origine = $PSScriptRoot
$Dest = Join-Path $env:LOCALAPPDATA "NerdNostalgia\Scanner"

function Titolo($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }

function Trova-Python {
    foreach ($c in @("py.exe", "python.exe")) {
        $t = Get-Command $c -ErrorAction SilentlyContinue
        # Gli alias del Microsoft Store (WindowsApps) non sono Python vero:
        # aprono lo Store, e dalla pianificazione non partono.
        if ($t -and $t.Source -notmatch "WindowsApps") { return $t.Source }
    }
    $c = Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1
    if ($c) { return $c.FullName }
    return $null
}

try {
    Write-Host "NerdNostalgia - Scanner carte: installazione" -ForegroundColor Magenta

    # --- 1. Python ---
    Titolo "1/6 Python"
    $py = Trova-Python
    if (-not $py) {
        if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
            throw "Python non c'e' e winget nemmeno. Installa Python da https://www.python.org/downloads/ (spunta 'Add python.exe to PATH') e rilancia Installa.cmd."
        }
        Write-Host "Python non trovato: lo installo (qualche minuto)..."
        winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")
        $py = Trova-Python
        if (-not $py) { throw "Python installato ma non trovato. Chiudi questa finestra e rilancia Installa.cmd." }
    }
    # Il percorso vero di python.exe (py.exe e' solo un lanciatore)
    $exe = (& $py -c "import sys; print(sys.executable)").Trim()
    $exeW = Join-Path (Split-Path $exe) "pythonw.exe"
    if (-not (Test-Path $exeW)) { $exeW = $exe }
    Write-Host "Python: $exe"
    Write-Host "Installo Pillow (per ridurre gli scan e leggere i TIFF)..."
    & $exe -m pip install --user --upgrade --disable-pip-version-check --quiet pillow
    if ($LASTEXITCODE -ne 0) { throw "Installazione di Pillow non riuscita (serve internet)." }

    # --- 2. File ---
    Titolo "2/6 Copio i file in $Dest"
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    foreach ($f in @("scanner_sync.py", "predefiniti.ini", "installa-scanner-sync.ps1", "Disinstalla.ps1", "Disinstalla.cmd", "LEGGIMI.txt")) {
        $src = Join-Path $Origine $f
        if (Test-Path $src) { Copy-Item $src $Dest -Force }
    }
    # Scaricati da internet: Windows li marca e chiederebbe conferma a ogni avvio.
    Get-ChildItem $Dest | Unblock-File
    $script = Join-Path $Dest "scanner_sync.py"

    # --- 3. Cartella dello scanner ---
    Titolo "3/6 Cartella dello scanner"
    Write-Host "Si apre una finestra: scegli la cartella dove lo scanner salva le carte."
    Add-Type -AssemblyName System.Windows.Forms
    $davanti = New-Object System.Windows.Forms.Form -Property @{ TopMost = $true }
    $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
    $dlg.Description = "Cartella dove lo scanner salva le carte (anche con sottocartelle Pokemon, Magic, YuGiOh, OnePiece)"
    $dlg.ShowNewFolderButton = $true
    if ($dlg.ShowDialog($davanti) -ne [System.Windows.Forms.DialogResult]::OK) { throw "Nessuna cartella scelta." }
    $cartella = $dlg.SelectedPath
    Write-Host "Cartella: $cartella"

    # --- 4. Configurazione ---
    Titolo "4/6 Configurazione"
    Write-Host "Invio = tieni il valore tra parentesi quadre."
    & $exe $script --configura --cartella $cartella
    if ($LASTEXITCODE -ne 0) { throw "Configurazione non salvata." }

    # --- 5. File gia' presenti ---
    Titolo "5/6 Carte gia' nella cartella"
    $nuovi = [int]((& $exe $script --conta) | Select-Object -Last 1)
    if ($nuovi -gt 0) {
        Write-Host "Nella cartella ci sono gia' $nuovi file mai caricati."
        $r = Read-Host "Caricarli al primo giro (C) o ignorarli e prendere solo quelli nuovi da oggi (I)? [C/I]"
        if ($r -match "^[iI]") {
            & $exe $script --segna-esistenti
            Write-Host "Ignorati: si parte dalle prossime scansioni."
        } else {
            Write-Host "Verranno caricati al primo giro."
        }
    } else {
        Write-Host "Nessun file da caricare per ora."
    }

    # --- 6. Pianificazione e icona ---
    Titolo "6/6 Pianificazione"
    $ora = Read-Host "A che ora ogni giorno? (invio = 21:00)"
    if (-not $ora) { $ora = "21:00" }
    if ($ora -notmatch "^\d{1,2}:\d{2}$") { throw "Ora non valida: usa il formato 21:00" }
    & (Join-Path $Dest "installa-scanner-sync.ps1") -Ora $ora -Python $exeW -Script $script

    $desktop = [Environment]::GetFolderPath("Desktop")
    $ws = New-Object -ComObject WScript.Shell
    $lnk = $ws.CreateShortcut((Join-Path $desktop "Carica carte adesso.lnk"))
    $lnk.TargetPath = $exe
    $lnk.Arguments = "`"$script`" --pausa"
    $lnk.WorkingDirectory = $Dest
    $lnk.Description = "Carica subito su NerdNostalgia le carte nuove della cartella dello scanner"
    $lnk.Save()
    Write-Host "Icona 'Carica carte adesso' sul desktop: per non aspettare il giro di stasera."

    Titolo "Fatto"
    $subito = Read-Host "Faccio un giro adesso? (S/n)"
    if ($subito -notmatch "^[nN]") { & $exe $script }
    Write-Host ""
    Write-Host "Log: $env:APPDATA\NerdNostalgia\scanner_sync.log"
    Write-Host "Per togliere tutto: Disinstalla.cmd in $Dest"
}
catch {
    Write-Host ""
    Write-Host "ERRORE: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Niente di grave: correggi e rilancia Installa.cmd."
    exit 1
}
