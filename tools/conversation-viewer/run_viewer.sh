#!/usr/bin/env bash
# Script to launch the Conversation & Token Viewer

set -e

# Change directory to the tool location
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=== AI Conversation & Token Viewer ==="
echo "[+] Starting local python server on port 8080..."

# Start the python server in the background
python3 viewer_server.py &
SERVER_PID=$!

# Trap exit signals to make sure we kill the server when script exits
trap "kill $SERVER_PID 2>/dev/null || true" EXIT

# Wait a brief moment for the server to spin up
sleep 1.5

echo "[+] Opening browser at http://localhost:8080..."
# Use python's webbrowser module to open the local dashboard in a platform-independent way
python3 -m webbrowser "http://localhost:8080" || xdg-open "http://localhost:8080" || open "http://localhost:8080" || true

echo "[+] Viewer running. Press Ctrl+C to stop."
wait $SERVER_PID
