#!/bin/bash
# Stop script for YouTube Downloader Service

set -e

PID_FILE="/var/run/youtube-downloader.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "Service is not running (no PID file found)"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ps -p "$PID" > /dev/null 2>&1; then
    echo "Stopping service (PID: $PID)..."
    kill "$PID"
    
    # Wait for process to stop
    for i in {1..10}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done
    
    # Force kill if still running
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Force killing process..."
        kill -9 "$PID"
    fi
    
    rm -f "$PID_FILE"
    echo "✓ Service stopped"
else
    echo "Service is not running (stale PID file)"
    rm -f "$PID_FILE"
fi
