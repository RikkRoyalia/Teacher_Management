$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Python environment not found. Create .venv and install requirements first."
}

Write-Host "Starting Teacher Management at http://127.0.0.1:8000/"
Write-Host "This server is bound to this computer only. Press Ctrl+C to stop."
& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
