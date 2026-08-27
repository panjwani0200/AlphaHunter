param(
    [string]$DatabaseName = 'nse_ai_trading',
    [string]$PostgresUser = 'postgres'
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$backendRoot = Join-Path $repoRoot 'backend'
$postgresRoot = 'C:\Program Files\PostgreSQL\16\bin'
$psql = Join-Path $postgresRoot 'psql.exe'

if (-not (Test-Path -LiteralPath $psql)) {
    $candidate = Get-ChildItem 'C:\Program Files\PostgreSQL' -Recurse -Filter psql.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($candidate) {
        $psql = $candidate.FullName
    } else {
        throw 'psql.exe was not found. Install PostgreSQL 16 or add psql to PATH.'
    }
}

Write-Output "Creating database '$DatabaseName' if needed..."
$env:PGPASSWORD = 'postgres'
$exists = (& $psql -h localhost -U $PostgresUser -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DatabaseName'" 2>$null | Out-String).Trim()
if ($exists -ne '1') {
    & $psql -h localhost -U $PostgresUser -d postgres -c "CREATE DATABASE $DatabaseName;"
}

Write-Output 'Running Alembic migrations...'
Push-Location $backendRoot
try {
    python -m alembic upgrade head
} finally {
    Pop-Location
}

Write-Output "Database '$DatabaseName' is ready."
