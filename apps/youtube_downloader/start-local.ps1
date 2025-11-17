# Start YouTube Downloader Service Locally (Windows)
# For testing before deploying to hstgr

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "YouTube Downloader Service - Local Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
$pythonVersion = python --version 2>&1
Write-Host "Python: $pythonVersion" -ForegroundColor White

# Check ffmpeg
$ffmpegCheck = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($ffmpegCheck) {
    Write-Host "ffmpeg: Found at $($ffmpegCheck.Source)" -ForegroundColor Green
} else {
    Write-Host "WARNING: ffmpeg not found. Install with: choco install ffmpeg" -ForegroundColor Yellow
    Write-Host "Or download from: https://ffmpeg.org/download.html" -ForegroundColor Yellow
}

Write-Host ""

# Navigate to service directory
$serviceDir = "apps\youtube_downloader"
if (-not (Test-Path $serviceDir)) {
    Write-Host "ERROR: Directory not found: $serviceDir" -ForegroundColor Red
    exit 1
}

Set-Location $serviceDir
Write-Host "Working directory: $(Get-Location)" -ForegroundColor White
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Install/update dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install --upgrade pip -q
pip install -r requirements.txt -q
Write-Host "✓ Dependencies installed" -ForegroundColor Green
Write-Host ""

# Set environment variables
$apiKey = "local-test-key-12345"
$env:YOUTUBE_DOWNLOADER_API_KEY = $apiKey
$env:PORT = "8080"
$env:HOST = "127.0.0.1"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  URL: http://127.0.0.1:8080" -ForegroundColor White
Write-Host "  API Key: $apiKey" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Starting service..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Start the service
python main.py
