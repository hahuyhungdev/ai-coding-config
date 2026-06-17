#!/usr/bin/env python3
import sys
import argparse
import secrets
import uvicorn
from server_hub.app import create_app
from server_hub.handler import ConfigHandler
from server_hub.metadata import get_all_conversations
from server_hub.parsers import parse_gemini_jsonl, parse_claude_jsonl, parse_codex_jsonl

app = create_app()

__all__ = [
    "app",
    "ConfigHandler",
    "get_all_conversations",
    "parse_gemini_jsonl",
    "parse_claude_jsonl",
    "parse_codex_jsonl",
]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Configuration Web Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the web server on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address to run the web server on")
    args = parser.parse_args()
    
    session_token = secrets.token_hex(32)
    app.state.session_token = session_token
    
    print(f"Starting FastAPI web server on http://{args.host}:{args.port}")
    print(f"Session token initialized.")
    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    except KeyboardInterrupt:
        print("\nStopping server.")
        sys.exit(0)
