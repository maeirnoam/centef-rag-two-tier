# Simple Frontend Deployment to Google Cloud Run

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CENTEF RAG - Frontend Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$PROJECT_ID = "sylvan-faculty-476113-c9"
$REGION = "us-central1"
$SERVICE_NAME = "centef-rag-frontend"

# Prompt for backend URL
Write-Host "Enter the Backend API URL:" -ForegroundColor Yellow
Write-Host "(Example: https://centef-rag-api-xxx-uc.a.run.app)" -ForegroundColor Gray
$BACKEND_URL = Read-Host "Backend URL"

if (-not $BACKEND_URL) {
    Write-Host "ERROR: Backend URL is required" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Project: $PROJECT_ID" -ForegroundColor White
Write-Host "Region: $REGION" -ForegroundColor White
Write-Host "Service: $SERVICE_NAME" -ForegroundColor White
Write-Host "Backend: $BACKEND_URL" -ForegroundColor White
Write-Host ""

# Step 1: Update frontend config with backend URL
Write-Host "[1/3] Updating frontend configuration..." -ForegroundColor Cyan

$authJsPath = "apps\frontend\js\auth.js"
$content = Get-Content $authJsPath -Raw
$content = $content -replace "const API_BASE_URL = '[^']*'", "const API_BASE_URL = '$BACKEND_URL'"
Set-Content -Path $authJsPath -Value $content

Write-Host "Frontend configured to use backend: $BACKEND_URL" -ForegroundColor Green
Write-Host ""

# Step 2: Build frontend Docker image
Write-Host "[2/3] Building frontend Docker image..." -ForegroundColor Cyan

$IMAGE_NAME = "us-central1-docker.pkg.dev/$PROJECT_ID/centef-rag/$SERVICE_NAME"

Set-Location "apps\frontend"
gcloud builds submit --tag $IMAGE_NAME --project $PROJECT_ID
Set-Location "..\..\"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Build failed" -ForegroundColor Red
    exit 1
}

Write-Host "Build successful!" -ForegroundColor Green
Write-Host ""

# Step 3: Deploy to Cloud Run
Write-Host "[3/3] Deploying to Cloud Run..." -ForegroundColor Cyan

gcloud run deploy $SERVICE_NAME `
    --image $IMAGE_NAME `
    --platform managed `
    --region $REGION `
    --allow-unauthenticated `
    --port 8080 `
    --memory 512Mi `
    --cpu 1 `
    --timeout 60 `
    --max-instances 5 `
    --project $PROJECT_ID

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Deployment failed" -ForegroundColor Red
    exit 1
}

Write-Host "Deployment successful!" -ForegroundColor Green
Write-Host ""

# Get service URL
$FRONTEND_URL = gcloud run services describe $SERVICE_NAME --region $REGION --format "value(status.url)" --project $PROJECT_ID

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Application URLs:" -ForegroundColor White
Write-Host "  Frontend: $FRONTEND_URL" -ForegroundColor Cyan
Write-Host "  Login:    $FRONTEND_URL/login.html" -ForegroundColor Gray
Write-Host "  Chat:     $FRONTEND_URL/chat.html" -ForegroundColor Gray
Write-Host ""
Write-Host "Test Accounts:" -ForegroundColor White
Write-Host "  Admin: admin@centef.org / Admin123!" -ForegroundColor Gray
Write-Host "  User:  user@centef.org / User123!" -ForegroundColor Gray
Write-Host ""
Write-Host "Open in browser: $FRONTEND_URL/login.html" -ForegroundColor Yellow
Write-Host ""
