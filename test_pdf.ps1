# Test PDF Processing Pipeline
# This script helps you upload and process a PDF through the CENTEF RAG system

$originalFilename = "Commentary_ The Dangers of Overreliance on Generative AI in the CT Fight.pdf"
$cleanFilename = "Commentary_The_Dangers_of_Overreliance_on_Generative_AI_in_the_CT_Fight.pdf"
$gcsPath = "gs://centef-rag-bucket/sources/$cleanFilename"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "CENTEF RAG - PDF Processing Test" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Original filename: $originalFilename" -ForegroundColor Yellow
Write-Host "Clean filename: $cleanFilename" -ForegroundColor Green
Write-Host "GCS destination: $gcsPath`n" -ForegroundColor Green

# Step 1: Ask for local file path
Write-Host "Step 1: Upload PDF to GCS" -ForegroundColor Cyan
$localPath = Read-Host "Enter the full path to the PDF file on your computer"

if (Test-Path $localPath) {
    Write-Host "✓ File found locally" -ForegroundColor Green
    
    # Upload to GCS
    Write-Host "Uploading to GCS..." -ForegroundColor Yellow
    gsutil cp "$localPath" "$gcsPath"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ File uploaded successfully`n" -ForegroundColor Green
    } else {
        Write-Host "✗ Upload failed`n" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✗ File not found: $localPath" -ForegroundColor Red
    Write-Host "`nPlease download the PDF from Google Drive first." -ForegroundColor Yellow
    exit 1
}

# Step 2: Run Python processing script
Write-Host "Step 2: Process PDF through CENTEF RAG pipeline" -ForegroundColor Cyan
Write-Host "This will:" -ForegroundColor White
Write-Host "  - Create manifest entry" -ForegroundColor Gray
Write-Host "  - Extract text with PyMuPDF" -ForegroundColor Gray
Write-Host "  - Create page-based chunks" -ForegroundColor Gray
Write-Host "  - Generate summary (TODO: needs Gemini integration)" -ForegroundColor Gray
Write-Host "  - Index to Vertex AI Search (TODO: needs Discovery Engine integration)`n" -ForegroundColor Gray

$proceed = Read-Host "Proceed with processing? (y/n)"

if ($proceed -eq 'y') {
    # Run the Python test script
    python test_pdf_processing.py
} else {
    Write-Host "`nProcessing cancelled. You can run it manually later with:" -ForegroundColor Yellow
    Write-Host "  python test_pdf_processing.py" -ForegroundColor Gray
}

Write-Host "`n========================================`n" -ForegroundColor Cyan
