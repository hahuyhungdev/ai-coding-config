"""Status check and token telemetry functions for AI Coding Config."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .cli import info, GREEN, RED, YELLOW, RESET
from .constants import CLAUDE_DIR, GEMINI_DIR


def get_latest_session_tokens() -> Optional[tuple[str, int]]:
    """Helper to calculate latest session token usage."""
    brain_dir = Path.home() / ".gemini" / "antigravity-cli" / "brain"
    if not brain_dir.exists() or not brain_dir.is_dir():
        return None
    
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
        return None
        
    transcript_path = latest_folder / ".system_generated" / "logs" / "transcript.jsonl"
    
    def estimate_tokens(text):
        if not text:
            return 0
        if not isinstance(text, str):
            text = str(text)
        chars = len(text)
        non_ascii = sum(1 for char in text if ord(char) > 127)
        return int(((chars - non_ascii) / 4.0) + (non_ascii / 1.5))

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
        return latest_folder.name, total_input_tokens
    except Exception:
        return None


def show_status() -> None:
    """Show configuration status, active account, and token usage."""
    info("AI Coding Config Status Check")
    print("=" * 60)
    
    # 1. Check AI Assistant Executables in PATH
    print("\n🔍 AI Assistants installation status:")
    for cli, name in [("claude", "Claude Code"), ("codex", "Codex CLI"), ("agy", "Antigravity CLI")]:
        path = shutil.which(cli)
        if path:
            print(f"  {GREEN}🟢 {name}{RESET}: Installed at {path}")
        else:
            print(f"  {RED}🔴 {name}{RESET}: Not found in $PATH")
            
    # 2. Check active Gemini/agy accounts
    print("\n👤 Active Gemini accounts (agyswap):")
    if shutil.which("agyswap") or shutil.which("agy"):
        try:
            res = subprocess.run(["agyswap", "list"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                print(res.stdout.strip())
            else:
                print("  (agyswap list failed or no accounts configured)")
        except Exception:
            print("  (Failed to query agyswap status)")
    else:
        print("  agyswap/agy not installed.")

    # 3. Check Token Budget for latest session
    print("\n🪙  Recent Gemini Token Budget & Telemetry:")
    latest_tokens = get_latest_session_tokens()
    if latest_tokens is not None:
        folder_name, tokens = latest_tokens
        print(f"  Latest session ({folder_name[:8]}): consumed {tokens:,} input tokens (Budget limit: 300,000)")
    else:
        print("  No recent Gemini session telemetry found.")

    # 4. Check Current Project Hook Status
    print("\n📁 Current directory project-level status:")
    cwd = Path.cwd()
    print(f"  Directory: {cwd}")
    
    graph_json = cwd / "graphify-out" / "graph.json"
    if graph_json.exists():
        print(f"  {GREEN}🟢 Graphify Graph{RESET}: Initialized ({graph_json.stat().st_size / 1024:.2f} KB)")
    else:
        print(f"  {YELLOW}🟡 Graphify Graph{RESET}: Not initialized in this directory")
        
    commit_hook = cwd / ".git" / "hooks" / "post-commit"
    checkout_hook = cwd / ".git" / "hooks" / "post-checkout"
    if commit_hook.exists() and checkout_hook.exists():
        print(f"  {GREEN}🟢 Git Hooks{RESET}: Graphify hooks are installed")
    else:
        print(f"  {YELLOW}🟡 Git Hooks{RESET}: Graphify hooks are NOT installed in this git repo")

    claude_settings = cwd / ".claude" / "settings.json"
    if claude_settings.exists():
        print(f"  {GREEN}🟢 Claude Hooks{RESET}: Project-level hooks configured in .claude/settings.json")
    else:
        print(f"  {YELLOW}🟡 Claude Hooks{RESET}: Project-level hooks NOT configured")

    print("\n" + "=" * 60)
