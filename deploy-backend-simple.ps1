# Simple Backend Deployment to Google Cloud Run

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CENTEF RAG - Backend Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$PROJECT_ID = "sylvan-faculty-476113-c9"
$REGION = "us-central1"
$SERVICE_NAME = "centef-rag-api"
$IMAGE_NAME = "us-central1-docker.pkg.dev/$PROJECT_ID/centef-rag/$SERVICE_NAME"

Write-Host "Project: $PROJECT_ID" -ForegroundColor White
Write-Host "Region: $REGION" -ForegroundColor White
Write-Host "Service: $SERVICE_NAME" -ForegroundColor White
Write-Host ""

# Step 1: Build and submit to Cloud Build from project root
Write-Host "[1/3] Building Docker image with Cloud Build..." -ForegroundColor Cyan
gcloud builds submit `
    --config apps/agent_api/cloudbuild.yaml `
    --substitutions _IMAGE_NAME=$IMAGE_NAME `
    --project $PROJECT_ID

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Build failed" -ForegroundColor Red
    exit 1
}

Write-Host "Build successful!" -ForegroundColor Green
Write-Host ""

# Step 2: Deploy to Cloud Run with environment variables from .env
Write-Host "[2/3] Deploying to Cloud Run..." -ForegroundColor Cyan

# Read .env file and build env vars argument
$envVars = @()
Get-Content ".env" | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#")) {
        if ($line -match "^([^=]+)=(.*)$") {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            # Remove quotes if present
            $value = $value -replace '^"|"$', ''
            $envVars += "$key=$value"
        }
    }
}

# Join with commas for gcloud
$envString = $envVars -join ","

# Add YOUTUBE_COOKIES_FILE to environment
$envString = "$envString,YOUTUBE_COOKIES_FILE=/tmp/yt-dlp/youtube_cookies.txt"

Write-Host "Setting environment variables from .env file..." -ForegroundColor Yellow

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
    --set-env-vars $envString `
    --project $PROJECT_ID

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Deployment failed" -ForegroundColor Red
    exit 1
}

Write-Host "Deployment successful!" -ForegroundColor Green
Write-Host ""

# Step 3: Get service URL and test
Write-Host "[3/3] Getting service URL..." -ForegroundColor Cyan
$SERVICE_URL = gcloud run services describe $SERVICE_NAME --region $REGION --format "value(status.url)" --project $PROJECT_ID

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend API URL:" -ForegroundColor White
Write-Host "  $SERVICE_URL" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test the API:" -ForegroundColor White
Write-Host "  Health: $SERVICE_URL/health" -ForegroundColor Gray
Write-Host "  Docs:   $SERVICE_URL/docs" -ForegroundColor Gray
Write-Host ""
Write-Host "Next: Deploy frontend with this backend URL" -ForegroundColor Yellow
Write-Host ""
