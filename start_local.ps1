# CENTEF RAG System - Local Deployment Startup

Write-Host "Starting CENTEF RAG System..." -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "apps\agent_api\main.py")) {
    Write-Host "Error: Please run this script from the centef-rag-fresh directory" -ForegroundColor Red
    exit 1
}

Write-Host "Directory check passed" -ForegroundColor Green
Write-Host ""

# Start backend in a new window
Write-Host "Starting Backend API Server..." -ForegroundColor Cyan
$backendCmd = "cd '$PWD\apps\agent_api'; `$env:PORT='8080'; python main.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

Write-Host "Backend starting at http://localhost:8080" -ForegroundColor Green
Write-Host "   (Opening in new terminal window)" -ForegroundColor Gray
Write-Host ""

# Wait a moment for backend to start
Write-Host "Waiting for backend to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Start frontend in a new window
Write-Host "Starting Frontend Server..." -ForegroundColor Cyan
$frontendCmd = "cd '$PWD\apps\frontend'; python serve.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host "Frontend starting at http://localhost:3000" -ForegroundColor Green
Write-Host "   (Opening in new terminal window)" -ForegroundColor Gray
Write-Host ""

# Wait for frontend to start
Start-Sleep -Seconds 2

# Open browser
Write-Host "Opening browser..." -ForegroundColor Cyan
Start-Process "http://localhost:3000/login.html"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CENTEF RAG System is running!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "URLs:" -ForegroundColor White
Write-Host "   Login:    http://localhost:3000/login.html" -ForegroundColor Gray
Write-Host "   Chat:     http://localhost:3000/chat.html" -ForegroundColor Gray
Write-Host "   Manifest: http://localhost:3000/manifest.html" -ForegroundColor Gray
Write-Host "   API:      http://localhost:8080" -ForegroundColor Gray
Write-Host ""
Write-Host "Sample Accounts:" -ForegroundColor White
Write-Host "   Admin:  admin@centef.org / Admin123!" -ForegroundColor Gray
Write-Host "   User:   user@centef.org / User123!" -ForegroundColor Gray
Write-Host ""
Write-Host "To stop the servers:" -ForegroundColor White
Write-Host "   Close the terminal windows or press Ctrl+C in each" -ForegroundColor Gray
Write-Host ""
