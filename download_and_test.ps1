# Download PDF from Google Drive and Process
# This script downloads the PDF from Google Drive and processes it

$driveFolder = "14L34ICYtH1GuH8CQQxhcL4uUpj2gZcuV"
$originalFilename = "Commentary_ The Dangers of Overreliance on Generative AI in the CT Fight.pdf"
$cleanFilename = "Commentary_The_Dangers_of_Overreliance_on_Generative_AI_in_the_CT_Fight.pdf"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "CENTEF RAG - Download & Process PDF" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Option 1: Use rclone (if configured)
Write-Host "Checking for rclone..." -ForegroundColor Yellow
if (Get-Command rclone -ErrorAction SilentlyContinue) {
    Write-Host "✓ rclone found" -ForegroundColor Green
    Write-Host "`nTo use rclone, you need to configure it first:" -ForegroundColor Yellow
    Write-Host "  rclone config" -ForegroundColor Gray
    Write-Host "  Then: rclone copy gdrive:folder/$originalFilename ." -ForegroundColor Gray
} else {
    Write-Host "✗ rclone not installed" -ForegroundColor Red
}

# Option 2: Use gdown (Python package)
Write-Host "`nChecking for gdown..." -ForegroundColor Yellow
$gdownCheck = python -c "import gdown" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ gdown is installed" -ForegroundColor Green
} else {
    Write-Host "✗ gdown not installed" -ForegroundColor Red
    Write-Host "Installing gdown..." -ForegroundColor Yellow
    pip install gdown
}

# Option 3: Manual download with link
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Google Drive Download Options:" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Option 1: Download manually" -ForegroundColor Yellow
Write-Host "  1. Go to: https://drive.google.com/drive/folders/$driveFolder" -ForegroundColor Gray
Write-Host "  2. Find: '$originalFilename'" -ForegroundColor Gray
Write-Host "  3. Download to your computer`n" -ForegroundColor Gray

Write-Host "Option 2: Use Google Drive for Desktop" -ForegroundColor Yellow
Write-Host "  If you have Google Drive synced, the file might already be at:" -ForegroundColor Gray
Write-Host "  G:\My Drive\<folder-name>\$originalFilename`n" -ForegroundColor Gray

Write-Host "Option 3: Get direct download link" -ForegroundColor Yellow
Write-Host "  1. Right-click the file in Google Drive" -ForegroundColor Gray
Write-Host "  2. Click 'Get link' and make sure it's shareable" -ForegroundColor Gray
Write-Host "  3. Provide me with the file ID or share link`n" -ForegroundColor Gray

Write-Host "========================================`n" -ForegroundColor Cyan

$choice = Read-Host "Which option? (1=manual, 2=drive-sync, 3=share-link)"

switch ($choice) {
    "1" {
        Write-Host "`nPlease download the file manually, then enter the path:" -ForegroundColor Yellow
        $localPath = Read-Host "Enter full path to downloaded PDF"
        
        if (Test-Path $localPath) {
            Write-Host "✓ File found!" -ForegroundColor Green
            
            # Upload to GCS
            $gcsPath = "gs://centef-rag-bucket/sources/$cleanFilename"
            Write-Host "Uploading to GCS: $gcsPath" -ForegroundColor Yellow
            gsutil cp "$localPath" "$gcsPath"
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ Upload successful!`n" -ForegroundColor Green
                
                # Ask to process
                $process = Read-Host "Process the PDF now? (y/n)"
                if ($process -eq 'y') {
                    python test_pdf_processing.py
                }
            }
        } else {
            Write-Host "✗ File not found: $localPath" -ForegroundColor Red
        }
    }
    
    "2" {
        Write-Host "`nEnter the full path to the file in your Google Drive folder:" -ForegroundColor Yellow
        $drivePath = Read-Host "Path (e.g., G:\My Drive\folder\file.pdf)"
        
        if (Test-Path $drivePath) {
            Write-Host "✓ File found in Google Drive sync!" -ForegroundColor Green
            
            # Upload to GCS
            $gcsPath = "gs://centef-rag-bucket/sources/$cleanFilename"
            Write-Host "Uploading to GCS: $gcsPath" -ForegroundColor Yellow
            gsutil cp "$drivePath" "$gcsPath"
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ Upload successful!`n" -ForegroundColor Green
                
                $process = Read-Host "Process the PDF now? (y/n)"
                if ($process -eq 'y') {
                    python test_pdf_processing.py
                }
            }
        } else {
            Write-Host "✗ File not found at: $drivePath" -ForegroundColor Red
        }
    }
    
    "3" {
        Write-Host "`nEnter the Google Drive file ID or share link:" -ForegroundColor Yellow
        $fileId = Read-Host "File ID or link"
        
        # Extract file ID from link if needed
        if ($fileId -match "id=([^&]+)") {
            $fileId = $matches[1]
        } elseif ($fileId -match "/d/([^/]+)") {
            $fileId = $matches[1]
        }
        
        Write-Host "Attempting to download with file ID: $fileId" -ForegroundColor Yellow
        
        # Try with gdown
        $outputPath = ".\$originalFilename"
        python -c "import gdown; gdown.download(id='$fileId', output='$outputPath', quiet=False)"
        
        if (Test-Path $outputPath) {
            Write-Host "✓ Downloaded successfully!" -ForegroundColor Green
            
            # Upload to GCS
            $gcsPath = "gs://centef-rag-bucket/sources/$cleanFilename"
            Write-Host "Uploading to GCS: $gcsPath" -ForegroundColor Yellow
            gsutil cp "$outputPath" "$gcsPath"
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ Upload successful!`n" -ForegroundColor Green
                
                $process = Read-Host "Process the PDF now? (y/n)"
                if ($process -eq 'y') {
                    python test_pdf_processing.py
                }
            }
        } else {
            Write-Host "✗ Download failed. The file might not be publicly accessible." -ForegroundColor Red
            Write-Host "Please make sure the file has 'Anyone with the link can view' permissions." -ForegroundColor Yellow
        }
    }
    
    default {
        Write-Host "Invalid option. Exiting." -ForegroundColor Red
    }
}

Write-Host "`n========================================`n" -ForegroundColor Cyan
