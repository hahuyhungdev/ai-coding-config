#!/usr/bin/env python3
"""
Zero-dependency Python HTTP Server to parse and visualize conversation transcripts.
Serves a responsive front-end dashboard and exposes JSON API endpoints.
"""

import http.server
import socketserver
import json
import os
import urllib.parse
from pathlib import Path
from datetime import datetime

PORT = 8080
BRAIN_DIR = Path.home() / ".gemini" / "antigravity-cli" / "brain"

def estimate_tokens(text: str, is_output=False) -> int:
    """Heuristic token estimator optimized for mixed English, code, and Vietnamese."""
    if not text:
        return 0
    chars = len(text)
    non_ascii = sum(1 for char in text if ord(char) > 127)
    ascii_len = chars - non_ascii
    
    # 4 chars per token for ASCII/English, 1.5 chars per token for Vietnamese/Unicode
    est = (ascii_len / 4.0) + (non_ascii / 1.5)
    return int(est)

def get_conversation_metadata(conv_dir: Path) -> dict:
    """Extract metadata and title snippet for a conversation directory."""
    log_file = conv_dir / ".system_generated" / "logs" / "transcript.jsonl"
    if not log_file.exists():
        return None
        
    mtime = log_file.stat().st_mtime
    dt = datetime.fromtimestamp(mtime)
    
    title = "Untitled Conversation"
    first_user_input = None
    
    try:
        with log_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("type") == "USER_INPUT":
                        content = data.get("content", "").strip()
                        if content:
                            # Strip USER_REQUEST wrapper tag if present
                            if "<USER_REQUEST>" in content:
                                content = content.split("<USER_REQUEST>")[-1].split("</USER_REQUEST>")[0].strip()
                            first_user_input = content
                            break
                except Exception:
                    continue
    except Exception:
        pass
        
    if first_user_input:
        title = first_user_input[:80] + "..." if len(first_user_input) > 80 else first_user_input
        
    return {
        "id": conv_dir.name,
        "title": title,
        "last_updated": dt.isoformat(),
        "size_bytes": log_file.stat().st_size
    }

class TranscriptAPIHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Allow CORS for easier local testing
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.end_headers()

    def do_GET(self):
        # Route API requests
        parsed_url = urllib.parse.urlparse(self.path)
        path_parts = parsed_url.path.strip("/").split("/")
        
        if len(path_parts) > 0 and path_parts[0] == "api":
            if len(path_parts) == 2 and path_parts[1] == "conversations":
                self.handle_list_conversations()
            elif len(path_parts) == 3 and path_parts[1] == "conversation":
                self.handle_get_conversation(path_parts[2])
            else:
                self.send_error(404, "API endpoint not found")
        else:
            path = urllib.parse.unquote(parsed_url.path).strip("/")
            if ".playwright-mcp" in path or ".gemini" in path:
                # Resolve file path
                if path.startswith("home/"):
                    file_path = Path("/") / path
                else:
                    file_path = Path.home() / path
                    if not file_path.exists():
                        file_path = Path(__file__).resolve().parents[2] / path

                if file_path.exists() and file_path.is_file():
                    content_type = "image/png" if file_path.suffix == ".png" else "application/octet-stream"
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(file_path.stat().st_size))
                    self.end_headers()
                    with file_path.open("rb") as f:
                        self.wfile.write(f.read())
                    return
                else:
                    self.send_error(404, "File not found")
                    return

            # Fallback to serving static files
            # Serve index.html if pointing at root
            if parsed_url.path == "/" or parsed_url.path == "":
                self.path = "/index.html"
            super().do_GET()

    def handle_list_conversations(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        conversations = []
        if BRAIN_DIR.exists() and BRAIN_DIR.is_dir():
            for child in BRAIN_DIR.iterdir():
                if child.is_dir():
                    meta = get_conversation_metadata(child)
                    if meta:
                        conversations.append(meta)
                        
        # Sort conversations by last updated descending
        conversations.sort(key=lambda x: x["last_updated"], reverse=True)
        self.wfile.write(json.dumps(conversations, indent=2).encode("utf-8"))

    def handle_get_conversation(self, conv_id):
        # Validate ID to prevent directory traversal
        clean_id = "".join(c for c in conv_id if c.isalnum() or c in "-_")
        log_file = BRAIN_DIR / clean_id / ".system_generated" / "logs" / "transcript.jsonl"
        
        if not log_file.exists():
            self.send_error(404, "Conversation log not found")
            return
            
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        # Determine model rates
        model_name = os.environ.get("ANTHROPIC_MODEL", "gemini-2.5-pro")
        model_lower = model_name.lower()
        if "pro" in model_lower: # e.g. gemini-2.5-pro, mimo-v2.5-pro
            input_rate = 1.25
            output_rate = 5.00
        elif "flash" in model_lower: # e.g. gemini-2.5-flash, deepseek-v4-flash
            input_rate = 0.075
            output_rate = 0.30
        elif "sonnet" in model_lower: # e.g. claude-3-5-sonnet, claude-3.7-sonnet
            input_rate = 3.00
            output_rate = 15.00
        elif "opus" in model_lower:
            input_rate = 15.00
            output_rate = 75.00
        elif "haiku" in model_lower:
            input_rate = 0.25
            output_rate = 1.25
        else:
            # Default to Gemini 2.5 Pro pricing
            input_rate = 1.25
            output_rate = 5.00

        steps = []
        stats = {
            "total_steps": 0,
            "user_messages": 0,
            "tool_calls": 0,
            "est_input_tokens": 0,
            "est_output_tokens": 0,
            "est_cost": 0.0,
            "model_name": model_name,
            "input_rate": input_rate,
            "output_rate": output_rate
        }
        
        # We will parse the transcript
        try:
            with log_file.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        step_type = data.get("type", "UNKNOWN")
                        content = data.get("content", "")
                        
                        # Calculate tokens
                        tokens = estimate_tokens(content)
                        data["est_tokens"] = tokens
                        
                        # Accumulate stats
                        stats["total_steps"] += 1
                        if step_type == "USER_INPUT":
                            stats["user_messages"] += 1
                            # Assume each user input sends a compacted context of ~25K tokens
                            stats["est_input_tokens"] += 25000 + tokens
                        elif step_type == "PLANNER_RESPONSE":
                            stats["est_output_tokens"] += tokens
                        elif step_type in (
                            "RUN_COMMAND", "VIEW_FILE", "GREP_SEARCH", "LIST_DIRECTORY",
                            "MCP_TOOL", "CODE_ACTION", "SEARCH_WEB", "READ_URL_CONTENT",
                            "ASK_QUESTION", "INVOKE_SUBAGENT", "CHECKPOINT", "ERROR_MESSAGE",
                            "LIST_RESOURCES", "GENERIC"
                        ):
                            if step_type != "CHECKPOINT":
                                stats["tool_calls"] += 1
                            # Tool/system responses count towards input tokens for the next turn
                            stats["est_input_tokens"] += tokens
                            
                        steps.append(data)
                    except Exception:
                        continue
        except Exception as e:
            self.send_error(500, f"Error reading transcript: {e}")
            return
            
        # Cost estimate based on model prices
        input_cost = (stats["est_input_tokens"] / 1_000_000.0) * input_rate
        output_cost = (stats["est_output_tokens"] / 1_000_000.0) * output_rate
        stats["est_cost"] = round(input_cost + output_cost, 4)
        
        payload = {
            "id": clean_id,
            "stats": stats,
            "steps": steps
        }
        self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))

def run():
    # Change working directory to this script's directory so simple file serving works
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    Handler = TranscriptAPIHandler
    # Avoid address already in use error
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"[viewer] Server started on port {PORT}")
        print(f"[viewer] Open http://localhost:{PORT} in your web browser")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[viewer] Server stopped.")

if __name__ == "__main__":
    run()
