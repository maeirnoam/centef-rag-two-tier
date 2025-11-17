# CENTEF RAG - Environment Verification & Deployment Test

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CENTEF RAG - Deployment Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$hasErrors = $false

# Check current directory
$currentDir = Get-Location
Write-Host "Current directory: $currentDir" -ForegroundColor Gray

# Navigate to centef-rag-fresh if needed
if ($currentDir.Path -notlike "*centef-rag-fresh") {
    if (Test-Path "centef-rag-fresh") {
        Set-Location "centef-rag-fresh"
        Write-Host "✓ Navigated to centef-rag-fresh" -ForegroundColor Green
    } else {
        Write-Host "✗ Cannot find centef-rag-fresh directory" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "[1/6] Checking .env file..." -ForegroundColor Cyan

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "✗ .env file not found" -ForegroundColor Red
    $hasErrors = $true
} else {
    Write-Host "✓ .env file exists" -ForegroundColor Green
    
    # Load and check required variables
    $requiredVars = @(
        "PROJECT_ID",
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
    
    $envContent = Get-Content ".env" -Raw
    $missingVars = @()
    
    foreach ($var in $requiredVars) {
        if ($envContent -notmatch "$var=.+") {
            $missingVars += $var
        }
    }
    
    if ($missingVars.Count -gt 0) {
        Write-Host "✗ Missing or empty variables:" -ForegroundColor Red
        foreach ($var in $missingVars) {
            Write-Host "  - $var" -ForegroundColor Yellow
        }
        $hasErrors = $true
    } else {
        Write-Host "✓ All required variables present" -ForegroundColor Green
    }
    
    # Check JWT_SECRET_KEY
    if ($envContent -match "JWT_SECRET_KEY=(.+)") {
        $jwtKey = $matches[1].Trim()
        if ($jwtKey -eq "your-secret-key-change-this-in-production-use-openssl-rand-hex-32") {
            Write-Host "⚠ Warning: JWT_SECRET_KEY is using default value" -ForegroundColor Yellow
            Write-Host "  Generate a secure key with:" -ForegroundColor Gray
            Write-Host "  -Join ((1..32 | ForEach-Object { '{0:x2}' -f (Get-Random -Max 256) }))" -ForegroundColor Gray
        } elseif ($jwtKey.Length -lt 32) {
            Write-Host "⚠ Warning: JWT_SECRET_KEY should be at least 32 characters" -ForegroundColor Yellow
        } else {
            Write-Host "✓ JWT_SECRET_KEY is configured" -ForegroundColor Green
        }
    }
    
    # Check datastore IDs have _gcs_store suffix
    if ($envContent -match "CHUNKS_DATASTORE_ID=(.+)") {
        $chunksId = $matches[1].Trim()
        if ($chunksId -notlike "*_gcs_store") {
            Write-Host "✗ CHUNKS_DATASTORE_ID must end with _gcs_store" -ForegroundColor Red
            $hasErrors = $true
        } else {
            Write-Host "✓ CHUNKS_DATASTORE_ID has correct suffix" -ForegroundColor Green
        }
    }
    
    if ($envContent -match "SUMMARIES_DATASTORE_ID=(.+)") {
        $summariesId = $matches[1].Trim()
        if ($summariesId -notlike "*_gcs_store") {
            Write-Host "✗ SUMMARIES_DATASTORE_ID must end with _gcs_store" -ForegroundColor Red
            $hasErrors = $true
        } else {
            Write-Host "✓ SUMMARIES_DATASTORE_ID has correct suffix" -ForegroundColor Green
        }
    }
}

Write-Host ""
Write-Host "[2/6] Checking gcloud CLI..." -ForegroundColor Cyan

# Check gcloud is installed
try {
    $gcloudVersion = gcloud version --format="value(core)" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ gcloud CLI is installed (version: $gcloudVersion)" -ForegroundColor Green
    } else {
        Write-Host "✗ gcloud CLI not found" -ForegroundColor Red
        Write-Host "  Install from: https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
        $hasErrors = $true
    }
} catch {
    Write-Host "✗ gcloud CLI not found" -ForegroundColor Red
    $hasErrors = $true
}

Write-Host ""
Write-Host "[3/6] Checking gcloud authentication..." -ForegroundColor Cyan

try {
    $account = gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null
    if ($account) {
        Write-Host "✓ Authenticated as: $account" -ForegroundColor Green
    } else {
        Write-Host "✗ No active authentication" -ForegroundColor Red
        Write-Host "  Run: gcloud auth login" -ForegroundColor Yellow
        $hasErrors = $true
    }
} catch {
    Write-Host "✗ Could not check authentication" -ForegroundColor Red
    $hasErrors = $true
}

Write-Host ""
Write-Host "[4/6] Checking PROJECT_ID..." -ForegroundColor Cyan

if ($env:PROJECT_ID) {
    Write-Host "✓ PROJECT_ID environment variable is set: $env:PROJECT_ID" -ForegroundColor Green
} else {
    # Try to get from .env
    if (Test-Path ".env") {
        $envContent = Get-Content ".env" -Raw
        if ($envContent -match "PROJECT_ID=(.+)") {
            $projectId = $matches[1].Trim()
            Write-Host "⚠ PROJECT_ID not in environment, but found in .env: $projectId" -ForegroundColor Yellow
            Write-Host "  Set it with: `$env:PROJECT_ID = '$projectId'" -ForegroundColor Gray
            
            # Set it for this session
            $env:PROJECT_ID = $projectId
            Write-Host "✓ PROJECT_ID set for this session" -ForegroundColor Green
        }
    } else {
        Write-Host "✗ PROJECT_ID not set" -ForegroundColor Red
        Write-Host "  Set it with: `$env:PROJECT_ID = 'your-project-id'" -ForegroundColor Yellow
        $hasErrors = $true
    }
}

Write-Host ""
Write-Host "[5/6] Checking deployment scripts..." -ForegroundColor Cyan

$scripts = @(
    "deploy-backend.ps1",
    "deploy-frontend.ps1",
    "test-docker-local.ps1"
)

foreach ($script in $scripts) {
    if (Test-Path $script) {
        Write-Host "✓ $script exists" -ForegroundColor Green
    } else {
        Write-Host "✗ $script not found" -ForegroundColor Red
        $hasErrors = $true
    }
}

Write-Host ""
Write-Host "[6/6] Checking Docker files..." -ForegroundColor Cyan

$dockerFiles = @(
    "apps/agent_api/Dockerfile",
    "apps/agent_api/.dockerignore",
    "apps/frontend/Dockerfile",
    "apps/frontend/.dockerignore"
)

foreach ($file in $dockerFiles) {
    if (Test-Path $file) {
        Write-Host "✓ $file exists" -ForegroundColor Green
    } else {
        Write-Host "✗ $file not found" -ForegroundColor Red
        $hasErrors = $true
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

if ($hasErrors) {
    Write-Host "❌ Verification FAILED" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Please fix the errors above before deploying." -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "✅ Verification PASSED" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Your environment is ready for deployment!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor White
    Write-Host ""
    Write-Host "Option 1 - Test locally first (recommended):" -ForegroundColor Cyan
    Write-Host "  .\test-docker-local.ps1" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Option 2 - Deploy to Cloud Run:" -ForegroundColor Cyan
    Write-Host "  .\deploy-backend.ps1" -ForegroundColor Gray
    Write-Host "  .\deploy-frontend.ps1" -ForegroundColor Gray
    Write-Host ""
    
    # Prompt for next action
    Write-Host "What would you like to do?" -ForegroundColor Yellow
    Write-Host "  1. Test locally with Docker (requires Docker installed)" -ForegroundColor Gray
    Write-Host "  2. Deploy backend to Cloud Run" -ForegroundColor Gray
    Write-Host "  3. Exit (I'll deploy manually later)" -ForegroundColor Gray
    Write-Host ""
    
    $choice = Read-Host "Enter your choice (1, 2, or 3)"
    
    switch ($choice) {
        "1" {
            Write-Host ""
            Write-Host "Starting local Docker test..." -ForegroundColor Cyan
            .\test-docker-local.ps1
        }
        "2" {
            Write-Host ""
            Write-Host "Starting Cloud Run deployment..." -ForegroundColor Cyan
            Write-Host ""
            .\deploy-backend.ps1
        }
        "3" {
            Write-Host ""
            Write-Host "Exiting. Run .\deploy-backend.ps1 when ready." -ForegroundColor Gray
        }
        default {
            Write-Host ""
            Write-Host "Invalid choice. Exiting." -ForegroundColor Yellow
            Write-Host "Run .\deploy-backend.ps1 when ready to deploy." -ForegroundColor Gray
        }
    }
}

Write-Host ""
