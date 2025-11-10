# Test Cloud Run Deployment Locally with Docker

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CENTEF RAG - Local Docker Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Load .env file
if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env file not found" -ForegroundColor Red
    Write-Host "Copy .env.example to .env and configure it" -ForegroundColor Yellow
    exit 1
}

Write-Host "Loading environment variables from .env..." -ForegroundColor Cyan
$envVars = @()
Get-Content ".env" | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim().Trim('"')
        $envVars += "-e"
        $envVars += "$key=$value"
    }
}

Write-Host "✓ Environment variables loaded" -ForegroundColor Green
Write-Host ""

# Test Backend
Write-Host "[1/2] Testing Backend Docker Build..." -ForegroundColor Cyan
Set-Location "apps\agent_api"

docker build -t centef-rag-api:test .

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Backend Docker build failed" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Backend Docker image built" -ForegroundColor Green
Write-Host ""

Write-Host "Starting backend container on port 8080..." -ForegroundColor Cyan
$envVars += @("-p", "8080:8080", "-e", "PORT=8080")
$containerId = docker run -d @envVars centef-rag-api:test

Write-Host "✓ Backend container started: $containerId" -ForegroundColor Green
Write-Host ""

Write-Host "Waiting for backend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host "Testing backend health endpoint..." -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8080/health"
    if ($response.status -eq "healthy") {
        Write-Host "✓ Backend health check passed!" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠ Backend health check failed: $_" -ForegroundColor Red
    Write-Host "Check logs: docker logs $containerId" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Backend is running at: http://localhost:8080" -ForegroundColor White
Write-Host "View logs: docker logs -f $containerId" -ForegroundColor Gray
Write-Host "Stop container: docker stop $containerId" -ForegroundColor Gray
Write-Host ""

# Test Frontend
Set-Location "..\frontend"

Write-Host "[2/2] Testing Frontend Docker Build..." -ForegroundColor Cyan
docker build -t centef-rag-frontend:test .

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Frontend Docker build failed" -ForegroundColor Red
    docker stop $containerId
    exit 1
}

Write-Host "✓ Frontend Docker image built" -ForegroundColor Green
Write-Host ""

Write-Host "Starting frontend container on port 3000..." -ForegroundColor Cyan
$frontendId = docker run -d -p 3000:8080 -e PORT=8080 centef-rag-frontend:test

Write-Host "✓ Frontend container started: $frontendId" -ForegroundColor Green
Write-Host ""

Write-Host "Waiting for frontend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host "Testing frontend..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000/login.html"
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Frontend is accessible!" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠ Frontend test failed: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Local Docker Test Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services Running:" -ForegroundColor White
Write-Host "  Backend:  http://localhost:8080" -ForegroundColor Gray
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Gray
Write-Host ""
Write-Host "Container IDs:" -ForegroundColor White
Write-Host "  Backend:  $containerId" -ForegroundColor Gray
Write-Host "  Frontend: $frontendId" -ForegroundColor Gray
Write-Host ""
Write-Host "Useful Commands:" -ForegroundColor White
Write-Host "  View backend logs:  docker logs -f $containerId" -ForegroundColor Gray
Write-Host "  View frontend logs: docker logs -f $frontendId" -ForegroundColor Gray
Write-Host "  Stop backend:       docker stop $containerId" -ForegroundColor Gray
Write-Host "  Stop frontend:      docker stop $frontendId" -ForegroundColor Gray
Write-Host "  Stop both:          docker stop $containerId $frontendId" -ForegroundColor Gray
Write-Host ""
Write-Host "Open in browser: http://localhost:3000/login.html" -ForegroundColor White
Write-Host ""

# Return to root
Set-Location "..\..\"
