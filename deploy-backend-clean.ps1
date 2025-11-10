# Deploy CENTEF RAG Backend API to Google Cloud Run
# Simple version without special characters

Write-Host "========================================"
Write-Host "CENTEF RAG - Backend API Deployment"
Write-Host "========================================"
Write-Host ""

# Configuration
$PROJECT_ID = $env:PROJECT_ID
$REGION = "us-central1"
$SERVICE_NAME = "centef-rag-api"
$REPO_NAME = "centef-rag"
$IMAGE_NAME = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$SERVICE_NAME"

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
Write-Host ""

# Step 0: Create Artifact Registry repository if it doesn't exist
Write-Host "[0/5] Setting up Artifact Registry..."
$repoExists = gcloud artifacts repositories describe $REPO_NAME --location=$REGION --project=$PROJECT_ID 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating Artifact Registry repository..."
    gcloud artifacts repositories create $REPO_NAME --repository-format=docker --location=$REGION --description="CENTEF RAG Docker images" --project=$PROJECT_ID
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to create Artifact Registry repository" -ForegroundColor Red
        exit 1
    }
    Write-Host "Repository created successfully" -ForegroundColor Green
} else {
    Write-Host "Repository already exists" -ForegroundColor Green
}
Write-Host ""

# Step 1: Prepare build context
Write-Host "[1/6] Preparing build context..."
# Copy requirements.txt to backend directory
Copy-Item "$PSScriptRoot\requirements.txt" "$PSScriptRoot\apps\agent_api\requirements.txt"
# Copy shared and tools directories to backend
Copy-Item -Recurse "$PSScriptRoot\shared" "$PSScriptRoot\apps\agent_api\shared" -Force
Copy-Item -Recurse "$PSScriptRoot\tools" "$PSScriptRoot\apps\agent_api\tools" -Force
Write-Host "Build context prepared" -ForegroundColor Green
Write-Host ""

# Step 2: Build Docker image
Write-Host "[2/6] Building Docker image..."
Set-Location "$PSScriptRoot\apps\agent_api"
gcloud builds submit --tag $IMAGE_NAME --project $PROJECT_ID

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker build failed" -ForegroundColor Red
    exit 1
}

Write-Host "Docker image built successfully" -ForegroundColor Green
Write-Host ""

# Cleanup copied files
Write-Host "Cleaning up build context..."
Remove-Item "$PSScriptRoot\apps\agent_api\requirements.txt" -ErrorAction SilentlyContinue
Remove-Item -Recurse "$PSScriptRoot\apps\agent_api\shared" -ErrorAction SilentlyContinue
Remove-Item -Recurse "$PSScriptRoot\apps\agent_api\tools" -ErrorAction SilentlyContinue
Set-Location $PSScriptRoot

# Step 3: Deploy to Cloud Run
Write-Host "[3/6] Deploying to Cloud Run..."

# Load environment variables from .env
$envPath = Join-Path $PSScriptRoot ".env"
$ENV_VARS = @()

if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim().Trim('"')
            $ENV_VARS += "$key=$value"
        }
    }
    Write-Host "Loaded $($ENV_VARS.Count) environment variables from .env"
} else {
    Write-Host "Warning: .env file not found at $envPath" -ForegroundColor Yellow
}

$env_vars_string = $ENV_VARS -join ','

Write-Host "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME --image $IMAGE_NAME --platform managed --region $REGION --allow-unauthenticated --port 8080 --memory 2Gi --cpu 2 --timeout 300 --max-instances 10 --set-env-vars $env_vars_string --project $PROJECT_ID

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Cloud Run deployment failed" -ForegroundColor Red
    exit 1
}

Write-Host "Deployed to Cloud Run successfully" -ForegroundColor Green
Write-Host ""

# Step 4: Get service URL
Write-Host "[4/6] Getting service URL..."
$SERVICE_URL = gcloud run services describe $SERVICE_NAME --region $REGION --format "value(status.url)" --project $PROJECT_ID

Write-Host "Service URL: $SERVICE_URL" -ForegroundColor Green
Write-Host ""

# Step 5: Test health endpoint
Write-Host "[5/6] Testing health endpoint..."
try {
    $response = Invoke-RestMethod -Uri "$SERVICE_URL/health" -Method Get
    if ($response.status -eq "healthy") {
        Write-Host "Health check passed!" -ForegroundColor Green
    } else {
        Write-Host "Health check returned unexpected response" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Health check failed: $_" -ForegroundColor Yellow
    Write-Host "Service may still be starting up..."
}

Write-Host ""
Write-Host "========================================"
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================"
Write-Host ""
Write-Host "API Endpoints:"
Write-Host "  Base URL:     $SERVICE_URL"
Write-Host "  Health:       $SERVICE_URL/health"
Write-Host "  Chat:         $SERVICE_URL/chat"
Write-Host "  Manifest:     $SERVICE_URL/manifest"
Write-Host ""
Write-Host "Next Steps:"
Write-Host "  1. Update frontend API_BASE_URL to: $SERVICE_URL"
Write-Host "  2. Deploy frontend with: .\deploy-frontend.ps1"
Write-Host "  3. Test API at: $SERVICE_URL/health"
Write-Host ""
