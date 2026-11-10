param([int]$Puerto=8013,[switch]$BaseExterna)
$ErrorActionPreference="Stop"
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
if (!(Test-Path -LiteralPath '.venv\Scripts\python.exe')) { throw 'Primero ejecuta scripts/configurar.ps1.' }
if (!$BaseExterna) { & .\.venv\Scripts\python.exe scripts/local_db.py start; if ($LASTEXITCODE -ne 0) { throw 'No se inició PostgreSQL.' } }
& .\.venv\Scripts\python.exe manage.py runserver "127.0.0.1:$Puerto" --nostatic
