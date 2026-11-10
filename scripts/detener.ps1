$ErrorActionPreference="Stop"
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
& .\.venv\Scripts\python.exe scripts/local_db.py stop
