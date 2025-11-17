# Test yt-dlp with command line to verify configuration
Write-Host "Testing yt-dlp with Firefox cookies..." -ForegroundColor Cyan
Write-Host ""

$cookiesPath = "$env:USERPROFILE\.cache\yt-dlp\youtube_cookies.txt"

if (Test-Path $cookiesPath) {
    Write-Host "✓ Cookies file found: $cookiesPath" -ForegroundColor Green
    $size = (Get-Item $cookiesPath).Length
    Write-Host "  Size: $size bytes" -ForegroundColor Gray
} else {
    Write-Host "✗ Cookies file not found: $cookiesPath" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Testing video: https://www.youtube.com/watch?v=qaGYZD2tWKM" -ForegroundColor White
Write-Host ""

# Test with yt-dlp CLI using mediaconnect client
$url = "https://www.youtube.com/watch?v=qaGYZD2tWKM"
$userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0'

yt-dlp `
    --cookies $cookiesPath `
    --user-agent $userAgent `
    --extractor-args 'youtube:player_client=mediaconnect,web' `
    --skip-download `
    --print 'title,duration,uploader' `
    $url

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==============================" -ForegroundColor Green
    Write-Host "✓ SUCCESS!" -ForegroundColor Green
    Write-Host "==============================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Configuration is working! Ready to deploy." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "==============================" -ForegroundColor Red
    Write-Host "✗ FAILED" -ForegroundColor Red
    Write-Host "==============================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Try refreshing cookies:" -ForegroundColor Yellow
    Write-Host "  python tools/setup_youtube_oauth.py" -ForegroundColor Gray
}
