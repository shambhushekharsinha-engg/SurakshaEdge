<#
.SYNOPSIS
  SurakshaEdge demo startup — Step 3 (API + dashboard) and Step 4 (pipeline with clip).

.USAGE
  # Step 3 — API + dashboard only (sim ALERT):
  .\scripts\start_demo.ps1

  # Step 4 — API + live clip (Gate G1):
  .\scripts\start_demo.ps1 -ClipPath data\clips\test1.mp4
#>
param(
    [string]$ClipPath = "",
    [string]$Config   = "configs/cpu.yaml",
    [int]   $Port     = 8000
)

Set-Location $PSScriptRoot\..

# ── 1. Environment ──────────────────────────────────────────────────────────
if (-not $env:SURAKSHA_KEY) {
    $env:SURAKSHA_KEY = python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"
    Write-Host "SURAKSHA_KEY generated (session only)" -ForegroundColor Yellow
}
$env:SURAKSHA_API_TOKEN = "demo-token"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║          SurakshaEdge Demo Launcher          ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── 2. Start API in background ───────────────────────────────────────────────
Write-Host "► Starting API on http://127.0.0.1:$Port ..." -ForegroundColor Green
$apiJob = Start-Job -ScriptBlock {
    param($port)
    Set-Location C:\SurakshaEdge\surakshaedge
    $env:SURAKSHA_KEY       = $using:env:SURAKSHA_KEY
    $env:SURAKSHA_API_TOKEN = "demo-token"
    python -m uvicorn surakshaedge.api.main:app --host 127.0.0.1 --port $port 2>&1
} -ArgumentList $Port

Start-Sleep -Seconds 3

# ── 3. Open browser ─────────────────────────────────────────────────────────
Write-Host "► Opening dashboard in browser..." -ForegroundColor Green
Start-Process "http://127.0.0.1:$Port"

Write-Host ""
Write-Host "Dashboard: http://127.0.0.1:$Port" -ForegroundColor Cyan
Write-Host "  • Click [🧪 Sim ALERT] to test the dashboard (Step 3)"
Write-Host "  • Banner should say '⚠ AUDIO: ENERGY FALLBACK'"
Write-Host ""

if ($ClipPath -ne "") {
    # ── 4. Run pipeline on clip (Gate G1) ────────────────────────────────────
    if (-not (Test-Path $ClipPath)) {
        Write-Host "ERROR: Clip not found: $ClipPath" -ForegroundColor Red
        Write-Host "Record a clip and place it at: $ClipPath"
        Stop-Job $apiJob; Remove-Job $apiJob
        exit 1
    }
    Write-Host "► Running pipeline on clip: $ClipPath" -ForegroundColor Green
    Write-Host "  Watch for ALERT on the dashboard map."
    Write-Host ""
    python -m surakshaedge.edge.pipeline --config $Config --source $ClipPath
    Write-Host ""
    Write-Host "Pipeline finished. Check the dashboard for ALERT events." -ForegroundColor Cyan
    Write-Host "If an ALERT appeared: take a screenshot and report G1 as met." -ForegroundColor Yellow
} else {
    Write-Host "Tip: To run Gate G1, add the clip path:" -ForegroundColor Yellow
    Write-Host "  .\scripts\start_demo.ps1 -ClipPath data\clips\test1.mp4" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Press Ctrl+C to stop the API server." -ForegroundColor Gray
    # Keep running until interrupted
    try {
        while ($true) {
            Start-Sleep -Seconds 5
            $out = Receive-Job $apiJob
            if ($out) { Write-Host $out }
        }
    } finally {
        Stop-Job $apiJob; Remove-Job $apiJob
    }
}

Stop-Job $apiJob -ErrorAction SilentlyContinue
Remove-Job $apiJob -ErrorAction SilentlyContinue
