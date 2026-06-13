import json
from datetime import datetime
from pathlib import Path
from .constants import BRAIN_DIR, CLAUDE_DIR, CODEX_DIR

def clean_project_name(folder_name: str) -> str:
    """Extract a clean project name from URL-encoded folder names."""
    if folder_name.startswith("-"):
        parts = [p for p in folder_name.split("-") if p]
        if parts:
            return parts[-1]
    return folder_name

def get_gemini_metadata(conv_dir: Path) -> dict:
    log_file = conv_dir / ".system_generated" / "logs" / "transcript.jsonl"
    if not log_file.exists():
        return None
        
    mtime = log_file.stat().st_mtime
    dt = datetime.fromtimestamp(mtime)
    
    title = "Untitled Gemini Conversation"
    try:
        with log_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("type") == "USER_INPUT":
                        content = data.get("content", "").strip()
                        if content:
                            if "<USER_REQUEST>" in content:
                                content = content.split("<USER_REQUEST>")[-1].split("</USER_REQUEST>")[0].strip()
                            title = content[:80] + "..." if len(content) > 80 else content
                            break
                except Exception:
                    continue
    except Exception:
        pass
        
    return {
        "id": f"gemini__{conv_dir.name}",
        "title": title,
        "last_updated": dt.isoformat(),
        "size_bytes": log_file.stat().st_size,
        "source": "gemini",
        "project": "Antigravity CLI"
    }

def get_claude_metadata(session_file: Path, project_dir_name: str) -> dict:
    mtime = session_file.stat().st_mtime
    dt = datetime.fromtimestamp(mtime)
    
    title = "Untitled Claude Conversation"
    try:
        with session_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("type") == "user" and "message" in data:
                        msg = data["message"]
                        role = msg.get("role")
                        if role == "user":
                            content = msg.get("content", "")
                            if isinstance(content, str) and content.strip():
                                if "❯" in content:
                                    content = content.replace("❯", "").strip()
                                title = content[:80] + "..." if len(content) > 80 else content
                                break
                except Exception:
                    continue
    except Exception:
        pass
        
    project_clean = clean_project_name(project_dir_name)
    return {
        "id": f"claude__{project_dir_name}__{session_file.stem}",
        "title": title,
        "last_updated": dt.isoformat(),
        "size_bytes": session_file.stat().st_size,
        "source": "claude",
        "project": project_clean
    }

def get_codex_metadata(rollout_file: Path, year: str, month: str, day: str) -> dict:
    mtime = rollout_file.stat().st_mtime
    dt = datetime.fromtimestamp(mtime)
    
    title = "Untitled Codex Conversation"
    project = "nx-monorepo-workspace"
    try:
        with rollout_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("type") == "session_meta" and "payload" in data:
                        cwd = data["payload"].get("cwd", "")
                        if cwd:
                            project = Path(cwd).name
                    if data.get("type") == "response_item" and "payload" in data:
                        payload = data["payload"]
                        if payload.get("type") == "message":
                            role = payload.get("role")
                            if role == "user":
                                for block in payload.get("content", []):
                                    if block.get("type") in ("input_text", "text"):
                                        content = block.get("text", "").strip()
                                        if content:
                                            if "❯" in content:
                                                content = content.replace("❯", "").strip()
                                            title = content[:80] + "..." if len(content) > 80 else content
                                            break
                                if title != "Untitled Codex Conversation":
                                    break
                except Exception:
                    continue
    except Exception:
        pass
        
    return {
        "id": f"codex__{year}-{month}-{day}__{rollout_file.stem}",
        "title": title,
        "last_updated": dt.isoformat(),
        "size_bytes": rollout_file.stat().st_size,
        "source": "codex",
        "project": project
    }

def get_all_conversations():
    conversations = []
    
    # 1. Gemini / Antigravity CLI
    if BRAIN_DIR.exists() and BRAIN_DIR.is_dir():
        for child in BRAIN_DIR.iterdir():
            if child.is_dir():
                meta = get_gemini_metadata(child)
                if meta:
                    conversations.append(meta)
                    
    # 2. Claude Code
    if CLAUDE_DIR.exists() and CLAUDE_DIR.is_dir():
        for project_dir in CLAUDE_DIR.iterdir():
            if project_dir.is_dir():
                for session_file in project_dir.glob("*.jsonl"):
                    meta = get_claude_metadata(session_file, project_dir.name)
                    if meta:
                        conversations.append(meta)
                        
    # 3. Codex CLI
    if CODEX_DIR.exists() and CODEX_DIR.is_dir():
        for year_dir in CODEX_DIR.iterdir():
            if year_dir.is_dir() and year_dir.name.isdigit():
                for month_dir in year_dir.iterdir():
                    if month_dir.is_dir() and month_dir.name.isdigit():
                        for day_dir in month_dir.iterdir():
                            if day_dir.is_dir() and day_dir.name.isdigit():
                                for rollout_file in day_dir.glob("*.jsonl"):
                                    meta = get_codex_metadata(rollout_file, year_dir.name, month_dir.name, day_dir.name)
                                    if meta:
                                        conversations.append(meta)
                                        
    conversations.sort(key=lambda x: x["last_updated"], reverse=True)
    return conversations
