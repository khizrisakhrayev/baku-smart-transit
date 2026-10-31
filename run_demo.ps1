# Starts Baku Smart Transit in demo mode on Windows.
# Usage (from the project folder):  powershell -ExecutionPolicy Bypass -File .\run_demo.ps1
# Optional: -Fresh starts with an empty demo database.
param([switch]$Fresh)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

# Load demo settings from .env.demo (KEY=VALUE lines; # starts a comment).
foreach ($line in Get-Content (Join-Path $root ".env.demo")) {
    $line = $line.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { continue }
    $name, $value = $line -split "=", 2
    Set-Item -Path "env:$($name.Trim())" -Value $value.Trim()
}

# Keep demo data separate from normal runs.
$env:DB_PATH = Join-Path $root "backend\demo.db"
if ($Fresh -and (Test-Path $env:DB_PATH)) { Remove-Item $env:DB_PATH }

# Use the project's virtual environment if there is one.
$python = Join-Path $root "venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

Write-Host "Demo: alert window $env:ANOMALY_WINDOW_SEC s, rush hour $env:RUSH_PERIOD_MIN min"
Write-Host "Opening http://127.0.0.1:8000/ (stop with Ctrl+C)"
Start-Process "http://127.0.0.1:8000/"

Set-Location (Join-Path $root "backend")
& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
