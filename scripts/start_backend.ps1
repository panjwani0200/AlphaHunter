param(
    [int]$Port = 8000
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$backendRoot = Join-Path $repoRoot 'backend'
$runDir = Join-Path $backendRoot '.run'
$pidFile = Join-Path $runDir 'uvicorn.pid'

New-Item -ItemType Directory -Force -Path $runDir | Out-Null

# Check if port is in use using netstat
$occupied = netstat -ano | Select-String ":$Port\s+" | Select-String "LISTENING"
if ($occupied) {
    throw "Port $Port is already in use."
}

# Robust native PowerShell path resolution for python.exe
$pythonPath = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonPath) {
    $pythonPath = "C:\Users\ayush\AppData\Local\Programs\Python\Python312\python.exe"
}

# Spawn uvicorn process using Start-Process to keep it in interactive session (enables headed Playwright scraper)
$process = Start-Process -FilePath $pythonPath -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port $Port" -WorkingDirectory $backendRoot -WindowStyle Hidden -PassThru

# Wait up to 10 seconds for uvicorn to become listening.
# Wait‑Process returns as soon as the process exits *or* the timeout expires.
$waitResult = Wait-Process -Id $process.Id -Timeout 10 -ErrorAction SilentlyContinue
if ($waitResult) {
    throw "uvicorn exited early with code $($process.ExitCode)."
}
$uvicornPid = $process.Id

if ($uvicornPid) {
    $uvicornPid | Set-Content -LiteralPath $pidFile
    Write-Output "Started backend PID $uvicornPid at http://127.0.0.1:$Port"
} else {
    throw "Failed to start backend server within 15 seconds."
}

