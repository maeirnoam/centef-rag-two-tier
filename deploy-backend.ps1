# Deploy CENTEF RAG Backend API to Google Cloud Run

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CENTEF RAG - Backend API Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$PROJECT_ID = $env:PROJECT_ID
$REGION = "us-central1"  # Change as needed
$SERVICE_NAME = "centef-rag-api"
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

# Navigate to backend directory
Set-Location "$PSScriptRoot\apps\agent_api"

# Step 1: Build Docker image
Write-Host "[1/4] Building Docker image..." -ForegroundColor Cyan
gcloud builds submit --tag $IMAGE_NAME --project $PROJECT_ID

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker build failed" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Docker image built successfully" -ForegroundColor Green
Write-Host ""

# Step 2: Deploy to Cloud Run
Write-Host "[2/4] Deploying to Cloud Run..." -ForegroundColor Cyan

# Load environment variables from .env
$ENV_VARS = @()
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim().Trim('"')
            $ENV_VARS += "$key=$value"
        }
    }
}

# Required environment variables for Cloud Run
$REQUIRED_VARS = @(
    "PROJECT_ID=$PROJECT_ID",
    "VERTEX_SEARCH_LOCATION",
    "GENERATION_LOCATION",
    "SUMMARY_MODEL",
    "GEMINI_MODEL",
    "CHUNKS_DATASTORE_ID",
    "SUMMARIES_DATASTORE_ID",
    "SOURCE_BUCKET",
    "TARGET_BUCKET",
    "CHAT_HISTORY_BUCKET",
    "JWT_SECRET_KEY"
)

Write-Host "Setting environment variables from .env..." -ForegroundColor Yellow

$env_vars_string = $ENV_VARS -join ','

gcloud run deploy $SERVICE_NAME `
    --image $IMAGE_NAME `
    --platform managed `
    --region $REGION `
    --allow-unauthenticated `
    --port 8080 `
    --memory 2Gi `
    --cpu 2 `
    --timeout 300 `
    --max-instances 10 `
    --set-env-vars $env_vars_string `
    --project $PROJECT_ID

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Cloud Run deployment failed" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Deployed to Cloud Run successfully" -ForegroundColor Green
Write-Host ""

# Step 3: Get service URL
Write-Host "[3/4] Getting service URL..." -ForegroundColor Cyan
$SERVICE_URL = gcloud run services describe $SERVICE_NAME --region $REGION --format "value(status.url)" --project $PROJECT_ID

Write-Host "✓ Service URL: $SERVICE_URL" -ForegroundColor Green
Write-Host ""

# Step 4: Test health endpoint
Write-Host "[4/4] Testing health endpoint..." -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "$SERVICE_URL/health" -Method Get
    if ($response.status -eq "healthy") {
        Write-Host "✓ Health check passed!" -ForegroundColor Green
    } else {
        Write-Host "⚠ Health check returned unexpected response" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ Health check failed: $_" -ForegroundColor Yellow
    Write-Host "  Service may still be starting up..." -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "API Endpoints:" -ForegroundColor White
Write-Host "  Base URL:     $SERVICE_URL" -ForegroundColor Gray
Write-Host "  Health:       $SERVICE_URL/health" -ForegroundColor Gray
Write-Host "  Chat:         $SERVICE_URL/chat" -ForegroundColor Gray
Write-Host "  Manifest:     $SERVICE_URL/manifest" -ForegroundColor Gray
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor White
Write-Host "  1. Update frontend API_BASE_URL to: $SERVICE_URL" -ForegroundColor Gray
Write-Host "  2. Deploy frontend with: .\deploy-frontend.ps1" -ForegroundColor Gray
Write-Host "  3. Test API at: $SERVICE_URL/health" -ForegroundColor Gray
Write-Host ""

# Return to original directory
Set-Location $PSScriptRoot
