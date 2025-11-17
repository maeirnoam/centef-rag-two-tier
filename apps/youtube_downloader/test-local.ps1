# Test External YouTube Downloader Service (Localhost)
# Quick test script for local development

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Testing YouTube Downloader (Localhost)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://127.0.0.1:8080"
$apiKey = "local-test-key-12345"

# Test 1: Health Check
Write-Host "[1/3] Testing health endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
    Write-Host "✓ Health check passed" -ForegroundColor Green
    Write-Host "  Status: $($response.status)" -ForegroundColor White
    Write-Host "  Pytubefix: $($response.pytubefix)" -ForegroundColor White
} catch {
    Write-Host "✗ Health check failed" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure the service is running:" -ForegroundColor Yellow
    Write-Host "  .\apps\youtube_downloader\start-local.ps1" -ForegroundColor White
    exit 1
}
Write-Host ""

# Test 2: Download metadata only
Write-Host "[2/3] Testing download endpoint (metadata)..." -ForegroundColor Yellow
$testUrl = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
$body = @{
    url = $testUrl
    video_id = "test123"
} | ConvertTo-Json

$headers = @{
    "X-API-Key" = $apiKey
    "Content-Type" = "application/json"
}

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/download" -Method Post -Body $body -Headers $headers
    if ($response.success) {
        Write-Host "✓ Metadata download successful" -ForegroundColor Green
        Write-Host "  Title: $($response.title)" -ForegroundColor White
    } else {
        Write-Host "✗ Download failed" -ForegroundColor Red
        Write-Host "  Error: $($response.error)" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ Metadata download failed" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 3: Download actual file
Write-Host "[3/3] Testing file download..." -ForegroundColor Yellow
Write-Host "  URL: $testUrl" -ForegroundColor White
Write-Host "  This may take 30-60 seconds..." -ForegroundColor Yellow

$outputFile = "test_download.wav"
try {
    Invoke-WebRequest -Uri "$baseUrl/download/file" `
        -Method Post `
        -Headers $headers `
        -Body $body `
        -OutFile $outputFile `
        -TimeoutSec 120
    
    if (Test-Path $outputFile) {
        $fileSize = (Get-Item $outputFile).Length
        $fileSizeMB = [math]::Round($fileSize / 1MB, 2)
        Write-Host "✓ File download successful" -ForegroundColor Green
        Write-Host "  File: $outputFile" -ForegroundColor White
        Write-Host "  Size: $fileSizeMB MB" -ForegroundColor White
        
        # Clean up
        Write-Host ""
        Write-Host "Cleaning up test file..." -ForegroundColor Yellow
        Remove-Item $outputFile
        Write-Host "✓ Test file removed" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ File download failed" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✓ Testing complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To use with Cloud Run backend:" -ForegroundColor Yellow
Write-Host "  1. Add to .env:" -ForegroundColor White
Write-Host "     YOUTUBE_DOWNLOADER_URL=http://127.0.0.1:8080" -ForegroundColor Gray
Write-Host "     YOUTUBE_DOWNLOADER_API_KEY=local-test-key-12345" -ForegroundColor Gray
Write-Host "  2. Run local backend:" -ForegroundColor White
Write-Host "     .\start-local.ps1" -ForegroundColor Gray
Write-Host "  3. Test YouTube upload via frontend" -ForegroundColor White
