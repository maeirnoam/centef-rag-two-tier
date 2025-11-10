# Kill any process using port 8080 and 3000, then start the system

Write-Host "Checking for processes using ports 8080 and 3000..." -ForegroundColor Cyan

# Kill process on port 8080
$port8080 = netstat -ano | findstr :8080 | Select-String "LISTENING" | ForEach-Object { $_.ToString().Trim() -split '\s+' | Select-Object -Last 1 }
if ($port8080) {
    Write-Host "Killing process on port 8080 (PID: $port8080)..." -ForegroundColor Yellow
    taskkill /PID $port8080 /F 2>$null
}

# Kill process on port 3000
$port3000 = netstat -ano | findstr :3000 | Select-String "LISTENING" | ForEach-Object { $_.ToString().Trim() -split '\s+' | Select-Object -Last 1 }
if ($port3000) {
    Write-Host "Killing process on port 3000 (PID: $port3000)..." -ForegroundColor Yellow
    taskkill /PID $port3000 /F 2>$null
}

Write-Host "Ports cleared!" -ForegroundColor Green
Write-Host ""

# Now run the startup script
.\start_local.ps1
