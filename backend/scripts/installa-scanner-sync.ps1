<#
  Pianifica scanner_sync.py una volta al giorno (Utilita' di pianificazione).

  Uso, da PowerShell nella cartella di questo file:
      .\installa-scanner-sync.ps1                 # ogni giorno alle 21:00
      .\installa-scanner-sync.ps1 -Ora 08:30      # a un'altra ora
      .\installa-scanner-sync.ps1 -Rimuovi        # toglie la pianificazione

  Se a quell'ora il PC e' spento, il giro parte appena si riaccende
  (StartWhenAvailable). Gira con il tuo utente, senza finestre (pythonw).
  Prima: python scanner_sync.py --configura
#>
param(
    [string]$Ora = "21:00",
    [switch]$Rimuovi,
    # Li passa l'installazione guidata (Installa.ps1); a mano si possono omettere.
    [string]$Python = "",
    [string]$Script = ""
)

$ErrorActionPreference = "Stop"
$Nome = "NerdNostalgia - Scanner carte"

if ($Rimuovi) {
    Unregister-ScheduledTask -TaskName $Nome -Confirm:$false
    Write-Host "Pianificazione rimossa."
    return
}

# pythonw = Python senza finestra. Il launcher pyw (installer di python.org)
# va bene uguale. Gli alias del Microsoft Store (cartella WindowsApps) dalla
# pianificazione spesso non partono: meglio l'installer di python.org.
$python = $null
if ($Python) { $python = $Python }
else { foreach ($c in @("pyw.exe", "pythonw.exe")) {
    $trovato = Get-Command $c -ErrorAction SilentlyContinue
    if ($trovato -and $trovato.Source -notmatch "WindowsApps") { $python = $trovato.Source; break }
} }
if (-not $python) {
    throw "Python non trovato (o solo quello del Microsoft Store). Installa Python da https://www.python.org/downloads/ spuntando 'Add python.exe to PATH'."
}

$script = if ($Script) { $Script } else { Join-Path $PSScriptRoot "scanner_sync.py" }
if (-not (Test-Path $script)) { throw "scanner_sync.py non trovato accanto a questo file." }

$azione = New-ScheduledTaskAction -Execute $python -Argument "`"$script`"" -WorkingDirectory (Split-Path $script)
$quando = New-ScheduledTaskTrigger -Daily -At $Ora
$opzioni = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName $Nome -Action $azione -Trigger $quando -Settings $opzioni `
    -Description "Carica le carte nuove della cartella dello scanner su NerdNostalgia" -Force | Out-Null

Write-Host "Pianificato ogni giorno alle $Ora con $python"
Write-Host "Per provarlo subito: Start-ScheduledTask -TaskName '$Nome'"
Write-Host "Log: $env:APPDATA\NerdNostalgia\scanner_sync.log"
