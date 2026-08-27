Write-Host "Building AlphaHunter Executable..." -ForegroundColor Cyan

# Clean previous builds
if (Test-Path -Path "build") { Remove-Item -Path "build" -Recurse -Force }
if (Test-Path -Path "dist") { Remove-Item -Path "dist" -Recurse -Force }

# Install pyinstaller if not present
if (!(Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    pip install pyinstaller
}

# Run PyInstaller
pyinstaller --clean alphahunter.spec

if ($?) {
    Write-Host "`nBuild Successful! Executable is located in dist/AlphaHunter.exe" -ForegroundColor Green
} else {
    Write-Host "`nBuild Failed!" -ForegroundColor Red
}
