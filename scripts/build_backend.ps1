$ErrorActionPreference = "Stop"

Write-Host "Building Python Backend with PyInstaller..."
Set-Location d:\AlphaHunter\backend

# Clean up previous builds
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

Write-Host "Activating virtual environment..."
. ".\.venv\Scripts\Activate.ps1"

pyinstaller --clean backend-x86_64-pc-windows-msvc.spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller failed."
    exit $LASTEXITCODE
}

Write-Host "Backend built successfully."
# Create src-tauri bin directory if it doesn't exist
$bin_dir = "..\src-tauri\bin"
if (-not (Test-Path $bin_dir)) { New-Item -ItemType Directory -Force $bin_dir | Out-Null }

Write-Host "Moving executable to $bin_dir..."
Copy-Item "dist\backend-x86_64-pc-windows-msvc.exe" -Destination "$bin_dir\" -Force

Write-Host "Done!"
