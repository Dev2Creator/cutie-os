# 🌸 CUTIE OS — Universal Windows PowerShell Installer 🌸
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  🌸 CUTIE OS — Installing the coziest terminal home on Windows... ✨" -ForegroundColor Magenta
Write-Host ""

# Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $pythonCmd) {
    Write-Host "  ✗ Python not found! Please install Python 3.8+ from https://python.org or winget install Python.Python.3.12" -ForegroundColor Red
    exit 1
}

$installDir = Join-Path $HOME ".cutie-os"
$binDir = Join-Path $HOME "AppData\Local\Microsoft\WindowsApps"

if (-not (Test-Path $installDir)) {
    New-Item -ItemType Directory -Path $installDir -Force | Out-Null
}

Write-Host "  ✦ Downloading CUTIE OS..." -ForegroundColor Cyan
$url = "https://raw.githubusercontent.com/Dev2Creator/cutie-os/main/cutie-os.py"
Invoke-WebRequest -Uri $url -OutFile (Join-Path $installDir "cutie-os.py")

# Create batch wrapper in WindowsApps (already on user PATH)
$cmdContent = "@echo off`r`npython `"$installDir\cutie-os.py`" %*"
Set-Content -Path (Join-Path $binDir "cutie.cmd") -Value $cmdContent

Write-Host "  ✓ Created launcher: cutie" -ForegroundColor Green
Write-Host ""
Write-Host "  ★ ✦ ★ CUTIE OS IS READY! ★ ✦ ★" -ForegroundColor Yellow
Write-Host "  Open Windows Terminal and type 'cutie' to launch! (˶ᵔ ᵕ ᵔ˶) ♡" -ForegroundColor Magenta
Write-Host ""
