param([string]$Python="python",[string]$PostgresBin="",[switch]$BaseExterna)
$ErrorActionPreference="Stop"
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
function Run-Python { param([string[]]$Arguments) & .\.venv\Scripts\python.exe @Arguments; if ($LASTEXITCODE -ne 0) { throw "Falló Python: $Arguments" } }
if (!(Test-Path -LiteralPath '.venv\Scripts\python.exe')) { & $Python -m venv .venv; if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear .venv. Usa Python 3.12 o superior.' } }
Run-Python -Arguments @('-m','pip','install','-r','requirements.txt')
if ($PostgresBin) { $env:POSTGRES_BIN=$PostgresBin }
Run-Python -Arguments @('scripts/local_db.py','config')
if (!$BaseExterna) { Run-Python -Arguments @('scripts/local_db.py','init') }
Run-Python -Arguments @('manage.py','migrate','--noinput')
Run-Python -Arguments @('manage.py','collectstatic','--noinput')
Run-Python -Arguments @('manage.py','seed_demo')
Write-Host 'Listo. Crea tu cuenta: .\.venv\Scripts\python.exe manage.py createsuperuser'
Write-Host 'Luego inicia con .\scripts\iniciar.ps1'
