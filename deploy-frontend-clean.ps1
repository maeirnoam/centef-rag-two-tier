# Deploy CENTEF RAG Frontend to Google Cloud Run
# Clean version without special characters

Write-Host "========================================"
Write-Host "CENTEF RAG - Frontend Deployment"
Write-Host "========================================"
Write-Host ""

# Configuration
$PROJECT_ID = $env:PROJECT_ID
$REGION = "us-central1"
$SERVICE_NAME = "centef-rag-frontend"
$REPO_NAME = "centef-rag"
$IMAGE_NAME = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$SERVICE_NAME"

# Get backend URL from user or use default
if (-not $env:BACKEND_URL) {
    Write-Host "Enter the backend API URL (or press Enter to use default):"
    $BACKEND_URL = Read-Host
    if (-not $BACKEND_URL) {
        $BACKEND_URL = "https://centef-rag-api-gac7qac6jq-uc.a.run.app"
    }
} else {
    $BACKEND_URL = $env:BACKEND_URL
}

# Check if PROJECT_ID is set
if (-not $PROJECT_ID) {
    Write-Host "ERROR: PROJECT_ID environment variable not set" -ForegroundColor Red
    Write-Host "Please set it with: `$env:PROJECT_ID='your-project-id'"
    exit 1
}

Write-Host "Configuration:"
Write-Host "  Project ID:   $PROJECT_ID"
Write-Host "  Region:       $REGION"
Write-Host "  Service:      $SERVICE_NAME"
Write-Host "  Repository:   $REPO_NAME"
Write-Host "  Image:        $IMAGE_NAME"
Write-Host "  Backend URL:  $BACKEND_URL"
Write-Host ""

# Step 1: Update frontend with backend URL
Write-Host "[1/5] Updating frontend configuration..."
$authJsPath = "$PSScriptRoot\apps\frontend\js\auth.js"
if (Test-Path $authJsPath) {
    $content = Get-Content $authJsPath -Raw
    $content = $content -replace "const API_BASE_URL = .*", "const API_BASE_URL = '$BACKEND_URL';"
    Set-Content $authJsPath $content
    Write-Host "Updated API_BASE_URL in auth.js" -ForegroundColor Green
} else {
    Write-Host "Warning: auth.js not found at $authJsPath" -ForegroundColor Yellow
}
Write-Host ""

# Step 2: Build Docker image
Write-Host "[2/5] Building Docker image..."
Set-Location "$PSScriptRoot\apps\frontend"
gcloud builds submit --tag $IMAGE_NAME --project $PROJECT_ID

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker build failed" -ForegroundColor Red
    Set-Location $PSScriptRoot
    exit 1
}

Write-Host "Docker image built successfully" -ForegroundColor Green
Write-Host ""

# Step 3: Deploy to Cloud Run
Write-Host "[3/5] Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME --image $IMAGE_NAME --platform managed --region $REGION --allow-unauthenticated --port 8080 --memory 512Mi --cpu 1 --timeout 60 --max-instances 5 --project $PROJECT_ID

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Cloud Run deployment failed" -ForegroundColor Red
    Set-Location $PSScriptRoot
    exit 1
}

Write-Host "Deployed to Cloud Run successfully" -ForegroundColor Green
Write-Host ""

# Step 4: Get service URL
Write-Host "[4/5] Getting service URL..."
$SERVICE_URL = gcloud run services describe $SERVICE_NAME --region $REGION --format "value(status.url)" --project $PROJECT_ID

Write-Host "Service URL: $SERVICE_URL" -ForegroundColor Green
Write-Host ""

# Step 5: Test frontend
Write-Host "[5/5] Testing frontend..."
try {
    $response = Invoke-WebRequest -Uri $SERVICE_URL -Method Get -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "Frontend is accessible!" -ForegroundColor Green
    } else {
        Write-Host "Frontend returned status: $($response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Could not reach frontend: $_" -ForegroundColor Yellow
    Write-Host "Service may still be starting up..."
}

Write-Host ""
Write-Host "========================================"
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================"
Write-Host ""
Write-Host "Frontend URL:     $SERVICE_URL" -ForegroundColor Cyan
Write-Host "Login Page:       $SERVICE_URL/login.html" -ForegroundColor Gray
Write-Host "Chat:             $SERVICE_URL/chat.html" -ForegroundColor Gray
Write-Host "Manifest:         $SERVICE_URL/manifest.html" -ForegroundColor Gray
Write-Host ""
Write-Host "Backend API:      $BACKEND_URL" -ForegroundColor White
Write-Host ""
Write-Host "Sample Accounts:" -ForegroundColor White
Write-Host "  Admin:  admin@centef.org / Admin123!" -ForegroundColor Gray
Write-Host "  User:   user@centef.org / User123!" -ForegroundColor Gray
Write-Host ""

# Return to original directory
Set-Location $PSScriptRoot
