#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

# Dracula Colors for terminal outputs
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

def estimate_tokens(text):
    if not text:
        return 0
    if not isinstance(text, str):
        text = str(text)
    chars = len(text)
    non_ascii = sum(1 for char in text if ord(char) > 127)
    ascii_len = chars - non_ascii
    return int((ascii_len / 4.0) + (non_ascii / 1.5))

def main():
    brain_dir = Path.home() / ".gemini" / "antigravity-cli" / "brain"
    if not brain_dir.exists() or not brain_dir.is_dir():
        return
    
    # Find the most recently updated session
    latest_folder = None
    latest_mtime = 0
    
    for folder in brain_dir.iterdir():
        if folder.is_dir():
            transcript_path = folder / ".system_generated" / "logs" / "transcript.jsonl"
            if transcript_path.exists():
                mtime = transcript_path.stat().st_mtime
                if mtime > latest_mtime:
                    latest_mtime = mtime
                    latest_folder = folder
                    
    if not latest_folder:
        return
        
    transcript_path = latest_folder / ".system_generated" / "logs" / "transcript.jsonl"
    
    # Parse transcript and calculate input tokens
    total_input_tokens = 0
    try:
        with transcript_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    step = json.loads(line)
                    stype = step.get("type")
                    content = step.get("content") or ""
                    tokens = estimate_tokens(content)
                    
                    if stype == "USER_INPUT":
                        total_input_tokens += 25000 + tokens
                    elif stype != "PLANNER_RESPONSE":
                        total_input_tokens += tokens
    except Exception:
        return
        
    # Warning Thresholds (budget warnings)
    # Default threshold: 300k tokens
    threshold = int(os.environ.get("GEMINI_TOKEN_BUDGET", "300000"))
    
    if total_input_tokens > threshold:
        print(f"\n{YELLOW}⚠️  GEMINI TOKEN WARNING:{RESET}", file=sys.stderr)
        print(f"Current session ({latest_folder.name[:8]}) has consumed {CYAN}{total_input_tokens:,}{RESET} input tokens.", file=sys.stderr)
        print(f"Running long agent loops increases cost and response latency.", file=sys.stderr)
        print(f"👉 {YELLOW}Recommendation:{RESET} Consider committing changes or restarting the session to clear the context window.\n", file=sys.stderr)

if __name__ == "__main__":
    main()
