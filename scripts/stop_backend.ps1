# Stop both the FastAPI server (8000) and the Playwright scraper service (8001)
foreach ($Port in @(8000, 8001)) {
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($connections) {
        foreach ($conn in $connections) {
            $targetPid = $conn.OwningProcess
            if ($targetPid -and $targetPid -ne 0) {
                $process = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
                if ($process) {
                    Stop-Process -Id $targetPid -Force
                    Write-Output "Stopped process PID $targetPid listening on port $Port"
                } else {
                    taskkill /f /pid $targetPid
                    Write-Output "Stopped process PID $targetPid via taskkill"
                }
            }
        }
    } else {
        # Fallback to netstat if Get-NetTCPConnection is unavailable or returns nothing
        $netstatConns = netstat -ano | Select-String ":$Port\s+"
        foreach ($conn in $netstatConns) {
            $line = $conn.Line.Trim()
            $parts = $line.Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)
            $targetPid = $parts[-1]
            if ($targetPid -match '^\d+$' -and $targetPid -ne 0) {
                $process = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
                if ($process) {
                    Stop-Process -Id $targetPid -Force
                    Write-Output "Stopped process PID $targetPid listening on port $Port (netstat)"
                } else {
                    taskkill /f /pid $targetPid
                    Write-Output "Stopped process PID $targetPid via taskkill (netstat)"
                }
            }
        }
    }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$pidFile = Join-Path $repoRoot 'backend\.run\uvicorn.pid'
Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
