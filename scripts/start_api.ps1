# ============================================================
# SurakshaEdge — API startup script (PowerShell)
# Run from the surakshaedge/ directory:
#   .\scripts\start_api.ps1
# ============================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- SURAKSHA_KEY -----------------------------------------------------------
# Generate a fresh key automatically if one hasn't been set yet.
if (-not $env:SURAKSHA_KEY) {
    $key = python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
    if (-not $key) {
        Write-Error "Python is required to generate SURAKSHA_KEY. Install Python 3.9+ and retry."
        exit 1
    }
    $env:SURAKSHA_KEY = $key
    Write-Host "[start_api] Generated new SURAKSHA_KEY (session-scoped)" -ForegroundColor Cyan
} else {
    Write-Host "[start_api] Using existing SURAKSHA_KEY from environment" -ForegroundColor DarkCyan
}

# --- SURAKSHA_API_TOKEN ------------------------------------------------------
if (-not $env:SURAKSHA_API_TOKEN) {
    $env:SURAKSHA_API_TOKEN = "demo-token"
    Write-Host "[start_api] SURAKSHA_API_TOKEN set to 'demo-token' (change for production)" -ForegroundColor Yellow
}

# --- SURAKSHA_CONFIG ---------------------------------------------------------
if (-not $env:SURAKSHA_CONFIG) {
    $env:SURAKSHA_CONFIG = "configs/demo.yaml"
}
Write-Host "[start_api] Config: $env:SURAKSHA_CONFIG" -ForegroundColor DarkGray

# --- SURAKSHA_PRODUCTION -----------------------------------------------------
if (-not $env:SURAKSHA_PRODUCTION) {
    $env:SURAKSHA_PRODUCTION = "false"
}

# --- Port --------------------------------------------------------------------
$port = if ($env:PORT) { $env:PORT } else { "8000" }

# --- Launch ------------------------------------------------------------------
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  SurakshaEdge API starting on http://localhost:$port" -ForegroundColor Green
Write-Host "  Dashboard : http://localhost:$port/" -ForegroundColor Green
Write-Host "  API docs  : http://localhost:$port/docs" -ForegroundColor Green
Write-Host "  Health    : http://localhost:$port/health" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

uvicorn main:app --host 0.0.0.0 --port $port --reload
