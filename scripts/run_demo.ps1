# SurakshaEdge - Demo startup script (PowerShell)
# Run from inside the surakshaedge/ directory with the venv active.
#
# =============================================================================
# PREREQUISITES
# =============================================================================
# 1. Install the package in editable mode (run once from C:\SurakshaEdge\):
#       pip install -e .
#
# 2. Download the YOLOv8n-pose model (run once from surakshaedge/ dir):
#       python -c "from ultralytics import YOLO; YOLO('yolov8n-pose.pt')"
#       # Then move/copy yolov8n-pose.pt into models/
#
# 3. Set the AES encryption key (required for privacy manager):
#       $env:SURAKSHA_KEY = python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"
#
# 4. (Optional) Set an API token (defaults to 'demo-token' if unset):
#       $env:SURAKSHA_API_TOKEN = "your-token-here"
#
# 5. Python modules used:
#       API server  : surakshaedge.api.main:app
#       Edge pipeline: surakshaedge.edge.pipeline
# =============================================================================

param(
    [string]$Config = "configs/demo.yaml",
    [string]$Source = ""
)

Write-Host "`n=== SurakshaEdge Demo ===" -ForegroundColor Cyan

# Environment setup
if (-not $env:SURAKSHA_KEY) {
    $env:SURAKSHA_KEY = python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"
    Write-Host "[ENV] Generated SURAKSHA_KEY" -ForegroundColor Yellow
}
if (-not $env:SURAKSHA_API_TOKEN) { $env:SURAKSHA_API_TOKEN = "demo-token" }
$env:SURAKSHA_CONFIG = $Config

# Terminal 1: API
Write-Host "[1/3] Launching API server on http://127.0.0.1:8000 ..." -ForegroundColor Green
$apiCmd = "cd '$PWD'; .venv\Scripts\Activate.ps1; `$env:SURAKSHA_API_TOKEN='$env:SURAKSHA_API_TOKEN'; `$env:SURAKSHA_KEY='$env:SURAKSHA_KEY'; `$env:SURAKSHA_CONFIG='$Config'; uvicorn surakshaedge.api.main:app --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $apiCmd
Start-Sleep -Seconds 2

# Terminal 2: Edge pipeline
$pipeCmd = if ($Source) {
    "cd '$PWD'; .venv\Scripts\Activate.ps1; `$env:SURAKSHA_API_TOKEN='$env:SURAKSHA_API_TOKEN'; `$env:SURAKSHA_KEY='$env:SURAKSHA_KEY'; python -m surakshaedge.edge.pipeline --config $Config --source $Source"
} else {
    "cd '$PWD'; .venv\Scripts\Activate.ps1; `$env:SURAKSHA_API_TOKEN='$env:SURAKSHA_API_TOKEN'; `$env:SURAKSHA_KEY='$env:SURAKSHA_KEY'; python -m surakshaedge.edge.pipeline --config $Config"
}
Write-Host "[2/3] Launching edge pipeline..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", $pipeCmd
Start-Sleep -Seconds 1

# Open dashboard
Write-Host "[3/3] Opening dashboard..." -ForegroundColor Green
Start-Process "http://127.0.0.1:8000"

Write-Host "`n✅ SurakshaEdge running!" -ForegroundColor Cyan
Write-Host "   Dashboard : http://127.0.0.1:8000"
Write-Host "   API docs  : http://127.0.0.1:8000/docs"
Write-Host "   Simulate  : POST /simulate with {`"scenario`":`"S1`",`"camera_id`":`"gate-1`"}"
Write-Host "`n   Use Ctrl+C in each terminal to stop.`n" -ForegroundColor Yellow
