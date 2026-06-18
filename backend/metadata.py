import json
import os
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

def resolve_gemini_transcript_path(gemini_id: str, brain_dir: Path = BRAIN_DIR) -> Path | None:
    log_dir = brain_dir / gemini_id / ".system_generated" / "logs"
    for filename in ("transcript_full.jsonl", "transcript.jsonl"):
        log_file = log_dir / filename
        if log_file.exists():
            return log_file
    return None

def describe_gemini_transcript_source(gemini_id: str, brain_dir: Path = BRAIN_DIR) -> dict | None:
    log_file = resolve_gemini_transcript_path(gemini_id, brain_dir=brain_dir)
    if log_file is None:
        return None

    try:
        relative_path = log_file.relative_to(brain_dir).as_posix()
    except ValueError:
        relative_path = log_file.name

    return {
        "kind": "full" if log_file.name == "transcript_full.jsonl" else "compact",
        "filename": log_file.name,
        "relative_path": relative_path,
    }


def get_gemini_metadata(conv_dir: Path) -> dict:
    log_file = resolve_gemini_transcript_path(conv_dir.name, brain_dir=conv_dir.parent)
    if not log_file or not log_file.exists():
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

def resolve_conversation_log(
    conv_id: str,
    brain_dir: Path | None = None,
    claude_dir: Path | None = None,
    codex_dir: Path | None = None,
) -> tuple[Path | None, str]:
    clean_id = "".join(c for c in conv_id if c.isalnum() or c in "-_")
    parts = clean_id.split("__")
    if len(parts) < 2:
        return None, "unknown"
        
    source = parts[0]
    if source == "gemini":
        gemini_id = parts[1]
        log_file = resolve_gemini_transcript_path(gemini_id, brain_dir=brain_dir or BRAIN_DIR)
        model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
        return log_file, model_name
        
    elif source == "claude":
        if len(parts) < 3:
            return None, "unknown"
        project_dir_name = parts[1]
        session_id = parts[2]
        c_dir = claude_dir or CLAUDE_DIR
        log_file = c_dir / project_dir_name / f"{session_id}.jsonl"
        
        model_name = "claude-3-5-sonnet"
        if log_file.exists():
            try:
                with log_file.open("r", encoding="utf-8") as f:
                    for line in f:
                        data = json.loads(line)
                        if data.get("type") == "assistant" and "message" in data:
                            model_name = data["message"].get("model", model_name)
                            break
            except Exception:
                pass
        return log_file, model_name
        
    elif source == "codex":
        if len(parts) < 3:
            return None, "unknown"
        year_month_day = parts[1]
        rollout_filename = parts[2]
        
        y_m_d_parts = year_month_day.split("-")
        if len(y_m_d_parts) != 3:
            return None, "unknown"
        year, month, day = y_m_d_parts
        
        cx_dir = codex_dir or CODEX_DIR
        log_file = cx_dir / year / month / day / f"{rollout_filename}.jsonl"
        
        model_name = "gpt-5"
        if log_file.exists():
            try:
                with log_file.open("r", encoding="utf-8") as f:
                    for line in f:
                        data = json.loads(line)
                        if data.get("type") == "session_meta" and "payload" in data:
                            model_name = data["payload"].get("model_provider", model_name)
                            break
            except Exception:
                pass
        return log_file, model_name
        
    return None, "unknown"


