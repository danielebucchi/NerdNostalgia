<#
  Toglie lo Scanner carte di NerdNostalgia da questo PC: pianificazione,
  icona sul desktop e file del programma. La configurazione e lo stato
  della cartella (%APPDATA%\NerdNostalgia) si tengono, a meno di dirlo:
  reinstallando, non si ricarica tutto da capo.
  NB: file in solo ASCII (vedi Installa.ps1).
#>
$Nome = "NerdNostalgia - Scanner carte"
$Dest = Join-Path $env:LOCALAPPDATA "NerdNostalgia\Scanner"

if (Get-ScheduledTask -TaskName $Nome -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $Nome -Confirm:$false
    Write-Host "Pianificazione tolta."
}
$lnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "Carica carte adesso.lnk"
if (Test-Path $lnk) { Remove-Item $lnk; Write-Host "Icona sul desktop tolta." }

$r = Read-Host "Cancello anche configurazione, password salvata e stato della cartella? (s/N)"
if ($r -match "^[sS]") {
    Remove-Item -Recurse -Force (Join-Path $env:APPDATA "NerdNostalgia") -ErrorAction SilentlyContinue
    Write-Host "Configurazione e stato cancellati."
}
# Per ultimo: questo script sta li' dentro.
Set-Location $env:TEMP
Remove-Item -Recurse -Force $Dest -ErrorAction SilentlyContinue
Write-Host "Scanner carte disinstallato."
