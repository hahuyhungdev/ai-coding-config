#!/usr/bin/env python3
import sys
import argparse
from http.server import ThreadingHTTPServer
from server_hub import ConfigHandler
from server_hub.metadata import get_all_conversations
from server_hub.parsers import parse_gemini_jsonl, parse_claude_jsonl, parse_codex_jsonl

__all__ = [
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
    
    import secrets
    session_token = secrets.token_hex(32)
    ConfigHandler.session_token = session_token
    
    server_address = (args.host, args.port)
    httpd = ThreadingHTTPServer(server_address, ConfigHandler)
    
    print(f"Starting standard library web server on http://{args.host}:{args.port}")
    print(f"Session token initialized.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        sys.exit(0)
