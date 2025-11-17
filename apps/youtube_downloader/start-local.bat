@echo off
REM Start YouTube Downloader Service Locally

echo ========================================
echo YouTube Downloader Service - Local Test
echo ========================================
echo.

REM Navigate to service directory
cd /d "%~dp0"

REM Check if venv exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo Virtual environment created
)

REM Activate venv and install dependencies
call venv\Scripts\activate.bat
echo Installing dependencies...
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo Dependencies installed
echo.

REM Set environment variables
set YOUTUBE_DOWNLOADER_API_KEY=local-test-key-12345
set PORT=8080
set HOST=127.0.0.1

echo ========================================
echo Configuration:
echo   URL: http://127.0.0.1:8080
echo   API Key: local-test-key-12345
echo ========================================
echo.
echo Starting service...
echo Press Ctrl+C to stop
echo.

REM Start the service
python main.py
