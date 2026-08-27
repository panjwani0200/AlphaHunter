param(
    [int]$Port = 8000
)

Write-Host "=== AlphaHunter Startup ===" -ForegroundColor Cyan

# Step 1: Kill anything on port 8000
Write-Host "Checking port $Port..." -ForegroundColor Yellow
$listening = netstat -ano | Select-String ":$Port\s+" | Select-String "LISTENING"
if ($listening) {
    $line = $listening.Line.Trim()
    $parts = $line -split '\s+'
    $oldPid = $parts[-1]
    Write-Host "Killing old process on port $Port (PID $oldPid)..." -ForegroundColor Yellow
    Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Step 2: Resolve Python path
$pythonPath = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonPath) {
    $pythonPath = "C:\Users\ayush\AppData\Local\Programs\Python\Python312\python.exe"
}
Write-Host "Using Python: $pythonPath" -ForegroundColor Gray

# Step 3: Start uvicorn in background
$backendRoot = Join-Path $PSScriptRoot '..\backend'
$backendRoot = Resolve-Path $backendRoot
Write-Host "Starting backend from: $backendRoot" -ForegroundColor Gray

$proc = Start-Process -FilePath $pythonPath `
    -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port $Port" `
    -WorkingDirectory $backendRoot `
    -WindowStyle Hidden `
    -PassThru

Write-Host "Backend process started (PID $($proc.Id)). Waiting for server to be ready..." -ForegroundColor Yellow

# Step 4: Poll until port is ready (up to 20 seconds)
$ready = $false
for ($i = 1; $i -le 20; $i++) {
    Start-Sleep -Seconds 1
    $check = netstat -ano | Select-String ":$Port\s+" | Select-String "LISTENING"
    if ($check) {
        $ready = $true
        break
    }
    Write-Host "  Waiting... ($i/20)" -ForegroundColor DarkGray
}

if (-not $ready) {
    Write-Host "ERROR: Backend did not start within 20 seconds." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "====================================================" -ForegroundColor Green
Write-Host "  AlphaHunter is LIVE!" -ForegroundColor Green
Write-Host "  Dashboard --> http://127.0.0.1:$Port/" -ForegroundColor Green
Write-Host "  API Docs  --> http://127.0.0.1:$Port/docs" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Opening dashboard in your browser..." -ForegroundColor Cyan
Start-Sleep -Seconds 3
Start-Process "http://127.0.0.1:$Port/"
