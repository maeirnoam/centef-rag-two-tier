# Deploy CENTEF RAG Frontend to Google Cloud Run

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CENTEF RAG - Frontend Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$PROJECT_ID = $env:PROJECT_ID
$REGION = "us-central1"  # Change as needed
$SERVICE_NAME = "centef-rag-frontend"
$IMAGE_NAME = "gcr.io/$PROJECT_ID/$SERVICE_NAME"

# Check if PROJECT_ID is set
if (-not $PROJECT_ID) {
    Write-Host "ERROR: PROJECT_ID environment variable not set" -ForegroundColor Red
    Write-Host "Please set it with: `$env:PROJECT_ID='your-project-id'" -ForegroundColor Yellow
    exit 1
}

Write-Host "Configuration:" -ForegroundColor White
Write-Host "  Project ID:   $PROJECT_ID" -ForegroundColor Gray
Write-Host "  Region:       $REGION" -ForegroundColor Gray
Write-Host "  Service:      $SERVICE_NAME" -ForegroundColor Gray
Write-Host "  Image:        $IMAGE_NAME" -ForegroundColor Gray
Write-Host ""

# Prompt for backend API URL
Write-Host "Enter the Backend API URL (from deploy-backend.ps1 output):" -ForegroundColor Yellow
$BACKEND_URL = Read-Host

if (-not $BACKEND_URL) {
    Write-Host "ERROR: Backend API URL is required" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Backend API URL: $BACKEND_URL" -ForegroundColor Gray
Write-Host ""

# Navigate to frontend directory
Set-Location "$PSScriptRoot\apps\frontend"

# Update API_BASE_URL in auth.js
Write-Host "[1/5] Updating API_BASE_URL in auth.js..." -ForegroundColor Cyan
$authJsPath = "js\auth.js"
$authJsContent = Get-Content $authJsPath -Raw
$authJsContent = $authJsContent -replace "const API_BASE_URL = '[^']*'", "const API_BASE_URL = '$BACKEND_URL'"
Set-Content $authJsPath $authJsContent
Write-Host "✓ API_BASE_URL updated to: $BACKEND_URL" -ForegroundColor Green
Write-Host ""

# Step 2: Build Docker image
Write-Host "[2/5] Building Docker image..." -ForegroundColor Cyan
gcloud builds submit --tag $IMAGE_NAME --project $PROJECT_ID

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker build failed" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Docker image built successfully" -ForegroundColor Green
Write-Host ""

# Step 3: Deploy to Cloud Run
Write-Host "[3/5] Deploying to Cloud Run..." -ForegroundColor Cyan

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
    Write-Host "ERROR: Cloud Run deployment failed" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Deployed to Cloud Run successfully" -ForegroundColor Green
Write-Host ""

# Step 4: Get service URL
Write-Host "[4/5] Getting service URL..." -ForegroundColor Cyan
$SERVICE_URL = gcloud run services describe $SERVICE_NAME --region $REGION --format "value(status.url)" --project $PROJECT_ID

Write-Host "✓ Service URL: $SERVICE_URL" -ForegroundColor Green
Write-Host ""

# Step 5: Test frontend
Write-Host "[5/5] Testing frontend..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "$SERVICE_URL/login.html" -Method Get
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Frontend is accessible!" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠ Frontend test failed: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Application URLs:" -ForegroundColor White
Write-Host "  Frontend:     $SERVICE_URL" -ForegroundColor Gray
Write-Host "  Login:        $SERVICE_URL/login.html" -ForegroundColor Gray
Write-Host "  Chat:         $SERVICE_URL/chat.html" -ForegroundColor Gray
Write-Host "  Manifest:     $SERVICE_URL/manifest.html" -ForegroundColor Gray
Write-Host ""
Write-Host "Backend API:      $BACKEND_URL" -ForegroundColor White
Write-Host ""
Write-Host "Sample Accounts:" -ForegroundColor White
Write-Host "  Admin:  admin@centef.org / Admin123!" -ForegroundColor Gray
Write-Host "  User:   user@centef.org / User123!" -ForegroundColor Gray
Write-Host ""

# Return to original directory
Set-Location $PSScriptRoot
