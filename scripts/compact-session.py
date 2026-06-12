#!/usr/bin/env python3
import json
import os
import sys
import shutil
from pathlib import Path

# Dracula colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
CYAN = "\033[96m"

def main():
    brain_dir = Path.home() / ".gemini" / "antigravity-cli" / "brain"
    if not brain_dir.exists() or not brain_dir.is_dir():
        print("Error: Antigravity CLI brain folder not found.", file=sys.stderr)
        sys.exit(1)
        
    # 1. Resolve session ID
    session_id = None
    if len(sys.argv) > 1 and sys.argv[1].strip():
        session_id = sys.argv[1].strip()
    else:
        # Find latest session folder
        latest_folder = None
        latest_mtime = 0
        for folder in brain_dir.iterdir():
            if folder.is_dir():
                t_path = folder / ".system_generated" / "logs" / "transcript.jsonl"
                if t_path.exists():
                    mtime = t_path.stat().st_mtime
                    if mtime > latest_mtime:
                        latest_mtime = mtime
                        latest_folder = folder
        if latest_folder:
            session_id = latest_folder.name
            
    if not session_id:
        print("Error: No session found to compact.", file=sys.stderr)
        sys.exit(1)
        
    session_dir = brain_dir / session_id
    transcript_path = session_dir / ".system_generated" / "logs" / "transcript.jsonl"
    backup_path = session_dir / ".system_generated" / "logs" / "transcript_pre_compact.jsonl"
    
    if not transcript_path.exists():
        print(f"Error: Transcript file not found at {transcript_path}", file=sys.stderr)
        sys.exit(1)
        
    # 2. Set limits
    max_lines = 100
    if len(sys.argv) > 2:
        try:
            max_lines = int(sys.argv[2])
        except ValueError:
            pass
            
    # Backup original before modifying
    if not backup_path.exists():
        shutil.copy2(transcript_path, backup_path)
        print(f"Created backup of original transcript at {backup_path}")
        
    # 3. Read and compact
    steps = []
    compacted_count = 0
    lines_removed_total = 0
    
    with transcript_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            step = json.loads(line)
            stype = step.get("type")
            content = step.get("content")
            
            # We compact tool result steps (e.g. view_file, run_command, grep_search)
            if stype in (
                "RUN_COMMAND", "VIEW_FILE", "GREP_SEARCH", "MCP_TOOL", 
                "CODE_ACTION", "SEARCH_WEB", "READ_URL_CONTENT"
            ) and content and isinstance(content, str):
                lines = content.splitlines()
                if len(lines) > max_lines:
                    keep_count = max_lines // 2
                    top_lines = lines[:keep_count]
                    bottom_lines = lines[-keep_count:]
                    
                    removed = len(lines) - (keep_count * 2)
                    lines_removed_total += removed
                    compacted_count += 1
                    
                    new_content = (
                        "\n".join(top_lines) + 
                        f"\n\n... [TRUNCATED {removed} LINES BY COMPACTION SCRIPT TO SAVE TOKENS] ...\n\n" + 
                        "\n".join(bottom_lines)
                    )
                    step["content"] = new_content
                    
            steps.append(step)
            
    # 4. Write back
    with transcript_path.open("w", encoding="utf-8") as f:
        for step in steps:
            f.write(json.dumps(step) + "\n")
            
    print(f"{GREEN}✓ Successfully compacted session {session_id[:8]}{RESET}")
    print(f"  - Compacted {CYAN}{compacted_count}{RESET} steps.")
    print(f"  - Removed {CYAN}{lines_removed_total:,}{RESET} lines of redundant tool output logs.")

if __name__ == "__main__":
    main()
