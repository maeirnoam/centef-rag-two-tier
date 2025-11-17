#!/bin/bash
# Start script for YouTube Downloader Service on hstgr

set -e

echo "========================================="
echo "YouTube Downloader Service - Startup"
echo "========================================="

# Configuration
SERVICE_DIR="/opt/youtube-downloader"
VENV_DIR="$SERVICE_DIR/venv"
LOG_DIR="/var/log/youtube-downloader"
PID_FILE="/var/run/youtube-downloader.pid"

# Create directories
mkdir -p "$LOG_DIR"
mkdir -p "$SERVICE_DIR"

# Check if running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Service is already running (PID: $PID)"
        exit 1
    fi
fi

# Setup virtual environment
echo "Setting up Python environment..."
cd "$SERVICE_DIR"

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# Install/update dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Start service
echo "Starting service..."
nohup python main.py > "$LOG_DIR/output.log" 2>&1 &
echo $! > "$PID_FILE"

echo "✓ Service started (PID: $(cat $PID_FILE))"
echo "Log: $LOG_DIR/output.log"
echo ""
echo "To check status: systemctl status youtube-downloader"
echo "To view logs: tail -f $LOG_DIR/output.log"
