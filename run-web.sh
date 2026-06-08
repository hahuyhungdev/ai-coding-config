#!/usr/bin/env bash
set -e

# Port configuration
PORT=${1:-8000}
HOST="127.0.0.1"

# Get script directory
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo -e "\033[94mℹ Starting AI Coding Configuration Web Dashboard...\033[0m"
echo -e "\033[94mℹ Server URL: http://$HOST:$PORT\033[0m"
echo -e "\033[94mℹ Press Ctrl+C to stop the server.\033[0m"
echo

# Kill any previous server instance running on the same port
echo -e "\033[90mℹ Cleaning up any stale server instances on port $PORT...\033[0m"
pkill -f "server.py --host $HOST --port $PORT" 2>/dev/null || true
sleep 0.5

# Run Python FastAPI server
python3 server.py --host "$HOST" --port "$PORT"
