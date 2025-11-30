#!/bin/bash

# Exit immediately if a command fails
set -e

# Move to the project root 
cd "$(dirname "$0")/.." || exit 1

# Activate the virtual environment
source .venv/bin/activate

# Define host and port
HOST="127.0.0.1"
PORT="8000"
URL="http://$HOST:$PORT"

# Start FastAPI app in the background
uvicorn backend.main:app --host $HOST --port $PORT --reload &

# Give server a moment to start
sleep 2

# Open the default browser (cross-platform)
if command -v xdg-open > /dev/null; then
    xdg-open $URL           # Linux
elif command -v open > /dev/null; then
    open $URL               # macOS
elif command -v start > /dev/null; then
    start $URL              # Windows (Git Bash)
else
    echo "Please open your browser and go to $URL"
fi

# Keep script alive until server is stopped
wait

