#!/usr/bin/env python3
import json
import subprocess
import sys
import argparse
import urllib.parse
import urllib.request
import shutil
import os
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import toml

REPO_DIR = Path(__file__).resolve().parent
SHARED_DISABLED = REPO_DIR / "shared-disabled-mcp.json"
AGENTS_DIR = REPO_DIR / "agents"
SKILLS_DIR = REPO_DIR / "skills"

BRAIN_DIR = Path.home() / ".gemini" / "antigravity-cli" / "brain"
CLAUDE_DIR = Path.home() / ".claude" / "projects"
CODEX_DIR = Path.home() / ".codex" / "sessions"

CLI_CONFIGS = {
    "claude": {"name": "Claude Code", "dir": "~/.claude"},
    "codex": {"name": "Codex CLI", "dir": "~/.codex"},
    "agy": {"name": "Antigravity", "dir": "~/.gemini"},
}


def get_all_mcp_servers() -> list[str]:
    defaults_path = REPO_DIR / "scripts" / "update-mcp-config.js"
    if defaults_path.exists():
        content = defaults_path.read_text()
        import re
        block = re.search(r'defaultServers\s*=\s*\{(.+?)\n\s*\};', content, re.DOTALL)
        if block:
            matches = re.findall(r'(?:\"([^\"]+)\"|\'([^\']+)\'|(\w[\w-]*))\s*:\s*\{', block.group(1))
            servers = [m[0] or m[1] or m[2] for m in matches]
            if servers:
                return servers
    return ["playwright", "context7", "memory", "sequential-thinking", "postgres", "sqlite", "docker", "aws"]


def load_disabled() -> list[str]:
    try:
        with open(SHARED_DISABLED) as f:
            return json.load(f).get("disabledMcpServers", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_disabled(disabled: list[str]) -> None:
    with open(SHARED_DISABLED, "w") as f:
        json.dump({"disabledMcpServers": sorted(disabled)}, f, indent=2)
        f.write("\n")


def get_mcp_servers() -> dict:
    try:
        with open(Path.home() / ".claude.json") as f:
            data = json.load(f)
            configs = {}
            configs.update(data.get("disabledMcpServers", {}))
            configs.update(data.get("mcpServers", {}))
            return configs
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_mcp_configs(updated_configs: dict, disabled_list: list[str]) -> None:
    claude_json_path = Path.home() / ".claude.json"
    try:
        data = {}
        if claude_json_path.exists():
            with open(claude_json_path) as f:
                data = json.load(f)
        
        mcp_servers = {}
        disabled_mcp_servers = {}
        
        for name, config in updated_configs.items():
            if name in disabled_list:
                disabled_mcp_servers[name] = config
            else:
                mcp_servers[name] = config
                
        data["mcpServers"] = mcp_servers
        data["disabledMcpServers"] = disabled_mcp_servers
        
        with open(claude_json_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    except Exception as e:
        print(f"Error saving MCP configs: {e}")


def list_agents() -> list[str]:
    if AGENTS_DIR.exists():
        return sorted([f.stem for f in AGENTS_DIR.glob("*.md")])
    return []


def list_skills() -> list[str]:
    if SKILLS_DIR.exists():
        return sorted([d.name for d in SKILLS_DIR.iterdir() if d.is_dir()])
    return []


def parse_markdown_frontmatter(path: Path) -> dict:
    if not path.exists():
        return {}
    metadata = {}
    try:
        content = path.read_text()
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        metadata[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return metadata


def load_claude_settings() -> dict:
    template_path = REPO_DIR / "claude" / "settings.json"
    try:
        with open(template_path) as f:
            return json.load(f)
    except Exception:
        return {}


def save_claude_settings(data: dict) -> None:
    template_path = REPO_DIR / "claude" / "settings.json"
    try:
        with open(template_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    except Exception:
        pass


def load_gemini_settings() -> dict:
    template_path = REPO_DIR / "gemini" / "settings.json"
    try:
        with open(template_path) as f:
            return json.load(f)
    except Exception:
        return {}


def save_gemini_settings(data: dict) -> None:
    template_path = REPO_DIR / "gemini" / "settings.json"
    try:
        with open(template_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    except Exception:
        pass



def load_codex_settings() -> dict:
    template_path = REPO_DIR / "codex" / "config.toml"
    try:
        with open(template_path) as f:
            return toml.load(f)
    except Exception:
        return {}


def update_toml_value(file_path: Path, section: str | None, key: str, value: any) -> None:
    if not file_path.exists():
        return
    lines = file_path.read_text().splitlines()
    
    current_section = None
    updated = False
    
    if isinstance(value, str):
        new_value_str = f'"{value}"'
    elif isinstance(value, bool):
        new_value_str = "true" if value else "false"
    else:
        new_value_str = str(value)
        
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped[1:-1].strip()
            continue
            
        if current_section == section:
            if "=" in line:
                parts = line.split("=", 1)
                k = parts[0].strip()
                if k == key:
                    comment = ""
                    if "#" in parts[1]:
                        comment = "  " + parts[1].split("#", 1)[1]
                    line_comment = f" #{comment}" if comment else ""
                    lines[i] = f"{parts[0].split('=')[0]}= {new_value_str}{line_comment}"
                    updated = True
                    break
                    
    if updated:
        file_path.write_text("\n".join(lines) + "\n")


def get_targets_state() -> dict:
    cli_state = {}
    for cid, info in CLI_CONFIGS.items():
        path_str = info["dir"].replace("~", str(Path.home()))
        cli_state[cid] = Path(path_str).exists()
    
    if not any(cli_state.values()):
        cli_state = {cid: True for cid in CLI_CONFIGS}
    return cli_state


def estimate_tokens(text: any, is_output=False) -> int:
    """Heuristic token estimator optimized for mixed English, code, and Vietnamese."""
    if not text:
        return 0
    if not isinstance(text, str):
        if isinstance(text, (list, dict)):
            text = json.dumps(text, ensure_ascii=False)
        else:
            text = str(text)
    chars = len(text)
    non_ascii = sum(1 for char in text if ord(char) > 127)
    ascii_len = chars - non_ascii
    
    # 4 chars per token for ASCII/English, 1.5 chars per token for Vietnamese/Unicode
    est = (ascii_len / 4.0) + (non_ascii / 1.5)
    return int(est)


ANALYTICS_CACHE = {}

def get_model_rates(model_name: str) -> tuple[float, float]:
    model_lower = model_name.lower()
    if "pro" in model_lower:
        return 1.25, 5.00
    elif "flash" in model_lower:
        return 0.075, 0.30
    elif "sonnet" in model_lower or "claude-3-5" in model_lower or "claude-3.7" in model_lower:
        return 3.00, 15.00
    elif "opus" in model_lower:
        return 15.00, 75.00
    elif "haiku" in model_lower:
        return 0.25, 1.25
    elif "gpt-5" in model_lower or "openai" in model_lower:
        return 5.00, 15.00
    else:
        return 1.25, 5.00

def get_session_analytics_stats(source: str, log_file: Path, model_name: str) -> dict:
    if not log_file.exists():
        return None
        
    mtime = log_file.stat().st_mtime
    cache_key = (source, str(log_file), mtime)
    if cache_key in ANALYTICS_CACHE:
        return ANALYTICS_CACHE[cache_key]
        
    steps = []
    if source == "gemini":
        steps = parse_gemini_jsonl(log_file)
    elif source == "claude":
        steps = parse_claude_jsonl(log_file)
    elif source == "codex":
        steps = parse_codex_jsonl(log_file)
        
    input_rate, output_rate = get_model_rates(model_name)
    
    total_steps = 0
    user_messages = 0
    tool_calls = 0
    est_input_tokens = 0
    est_output_tokens = 0
    
    for step in steps:
        content = step.get("content") or ""
        tokens = estimate_tokens(content)
        
        total_steps += 1
        step_type = step.get("type")
        if step_type == "USER_INPUT":
            user_messages += 1
            est_input_tokens += 25000 + tokens
        elif step_type == "PLANNER_RESPONSE":
            est_output_tokens += tokens
        elif step_type in (
            "RUN_COMMAND", "VIEW_FILE", "GREP_SEARCH", "LIST_DIRECTORY",
            "MCP_TOOL", "CODE_ACTION", "SEARCH_WEB", "READ_URL_CONTENT",
            "ASK_QUESTION", "INVOKE_SUBAGENT", "CHECKPOINT", "ERROR_MESSAGE",
            "LIST_RESOURCES", "GENERIC"
        ):
            if step_type != "CHECKPOINT":
                tool_calls += 1
            est_input_tokens += tokens
            
    input_cost = (est_input_tokens / 1_000_000.0) * input_rate
    output_cost = (est_output_tokens / 1_000_000.0) * output_rate
    est_cost = round(input_cost + output_cost, 4)
    
    stats = {
        "steps": total_steps,
        "turns": user_messages,
        "tool_calls": tool_calls,
        "input_tokens": est_input_tokens,
        "output_tokens": est_output_tokens,
        "total_tokens": est_input_tokens + est_output_tokens,
        "cost": est_cost,
        "model_name": model_name
    }
    
    ANALYTICS_CACHE[cache_key] = stats
    return stats

def get_aggregate_analytics():
    conversations = get_all_conversations()
    session_stats = []
    
    total_sessions = 0
    total_steps = 0
    total_turns = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0
    
    for conv in conversations:
        conv_id = conv["id"]
        parts = conv_id.split("__")
        if len(parts) < 2:
            continue
        source = parts[0]
        
        log_file = None
        model_name = "unknown"
        
        if source == "gemini":
            gemini_id = parts[1]
            log_file = BRAIN_DIR / gemini_id / ".system_generated" / "logs" / "transcript.jsonl"
            model_name = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
        elif source == "claude":
            project_dir_name = parts[1]
            session_id = parts[2]
            log_file = CLAUDE_DIR / project_dir_name / f"{session_id}.jsonl"
            model_name = "claude-3-5-sonnet"
            try:
                with log_file.open("r", encoding="utf-8") as f:
                    for line in f:
                        data = json.loads(line)
                        if data.get("type") == "assistant" and "message" in data:
                            model_name = data["message"].get("model", model_name)
                            break
            except Exception:
                pass
        elif source == "codex":
            year_month_day = parts[1]
            rollout_filename = parts[2]
            y_m_d_parts = year_month_day.split("-")
            if len(y_m_d_parts) == 3:
                year, month, day = y_m_d_parts
                log_file = CODEX_DIR / year / month / day / f"{rollout_filename}.jsonl"
                model_name = "gpt-5"
                try:
                    with log_file.open("r", encoding="utf-8") as f:
                        for line in f:
                            data = json.loads(line)
                            if data.get("type") == "session_meta" and "payload" in data:
                                model_name = data["payload"].get("model_provider", model_name)
                                break
                except Exception:
                    pass
                    
        if log_file and log_file.exists():
            stats = get_session_analytics_stats(source, log_file, model_name)
            if stats:
                total_sessions += 1
                total_steps += stats["steps"]
                total_turns += stats["turns"]
                total_input_tokens += stats["input_tokens"]
                total_output_tokens += stats["output_tokens"]
                total_cost += stats["cost"]
                
                session_stats.append({
                    "id": conv_id,
                    "title": conv["title"],
                    "last_updated": conv["last_updated"],
                    "size_bytes": conv["size_bytes"],
                    "source": conv["source"],
                    "project": conv["project"],
                    "steps": stats["steps"],
                    "turns": stats["turns"],
                    "tool_calls": stats["tool_calls"],
                    "input_tokens": stats["input_tokens"],
                    "output_tokens": stats["output_tokens"],
                    "total_tokens": stats["total_tokens"],
                    "cost": stats["cost"],
                    "model_name": stats["model_name"]
                })
                
    session_stats.sort(key=lambda x: x["last_updated"], reverse=True)
    
    return {
        "total_sessions": total_sessions,
        "total_steps": total_steps,
        "total_turns": total_turns,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_cost": round(total_cost, 4),
        "sessions": session_stats
    }


def clean_project_name(folder_name: str) -> str:
    """Extract a clean project name from URL-encoded folder names."""
    if folder_name.startswith("-"):
        parts = [p for p in folder_name.split("-") if p]
        if parts:
            return parts[-1]
    return folder_name


def map_tool_name_to_step_type(tool_name: str) -> str:
    """Map various tool names from different CLIs to a unified step type."""
    name_lower = tool_name.lower()
    if name_lower in ("bash", "execute_command", "run_command", "run_shell_command"):
        return "RUN_COMMAND"
    elif name_lower in ("read", "view_file", "read_file", "get_file_contents"):
        return "VIEW_FILE"
    elif name_lower in ("grep", "grep_search", "search_code", "search_issues"):
        return "GREP_SEARCH"
    elif name_lower in ("list", "list_directory", "list_dir"):
        return "LIST_DIRECTORY"
    elif name_lower in ("replace_file_content", "write_to_file", "multi_replace_file_content", "apply_patch", "edit_file", "create_or_update_file", "push_files"):
        return "CODE_ACTION"
    elif name_lower in ("search_web", "google_search", "search_repositories"):
        return "SEARCH_WEB"
    elif name_lower in ("read_url_content", "read_url", "read_browser_page"):
        return "READ_URL_CONTENT"
    elif name_lower in ("ask_question", "ask_permission"):
        return "ASK_QUESTION"
    elif name_lower in ("invoke_subagent", "define_subagent"):
        return "INVOKE_SUBAGENT"
    elif name_lower in ("list_resources", "list_permissions"):
        return "LIST_RESOURCES"
    else:
        return "MCP_TOOL"


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


def parse_gemini_jsonl(log_file: Path) -> list:
    steps = []
    try:
        with log_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    steps.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        pass

    # Post-process to associate tool calls args with execution steps
    pending_tool_calls = []
    for step in steps:
        step_type = step.get("type")
        if step_type == "PLANNER_RESPONSE":
            tool_calls = step.get("tool_calls", [])
            for tc in tool_calls:
                tc_name = tc.get("name")
                tc_args = tc.get("args", {})
                # Clean up string-wrapped arguments if they are double-quoted
                cleaned_args = {}
                if isinstance(tc_args, dict):
                    for k, v in tc_args.items():
                        if isinstance(v, str):
                            v_clean = v.strip()
                            if (v_clean.startswith('"') and v_clean.endswith('"')) or (v_clean.startswith("'") and v_clean.endswith("'")):
                                try:
                                    v_unquoted = json.loads(v_clean)
                                    if isinstance(v_unquoted, str):
                                        v_clean = v_unquoted
                                    else:
                                        v_clean = v_clean[1:-1]
                                except Exception:
                                    v_clean = v_clean[1:-1]
                            cleaned_args[k] = v_clean
                        else:
                            cleaned_args[k] = v
                else:
                    cleaned_args = tc_args
                pending_tool_calls.append({
                    "name": tc_name,
                    "args": cleaned_args
                })
        elif step_type not in ("USER_INPUT", "PLANNER_RESPONSE", "CONVERSATION_HISTORY"):
            # This is a tool execution step. Find the first pending tool call that matches.
            matched_idx = -1
            for i, tc in enumerate(pending_tool_calls):
                mapped_type = map_tool_name_to_step_type(tc["name"])
                if mapped_type == step_type:
                    matched_idx = i
                    break
            
            if matched_idx != -1:
                tc = pending_tool_calls.pop(matched_idx)
                step["resolved_args"] = tc["args"]
                step["name"] = tc["name"]
            elif pending_tool_calls:
                tc = pending_tool_calls.pop(0)
                step["resolved_args"] = tc["args"]
                step["name"] = tc["name"]

    return steps


def parse_claude_jsonl(log_file: Path) -> list:
    steps = []
    tool_calls_map = {}
    try:
        with log_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    line_type = data.get("type")
                    
                    if line_type == "user" and "message" in data:
                        msg = data["message"]
                        role = msg.get("role")
                        if role == "user":
                            content = msg.get("content", "")
                            if isinstance(content, list):
                                for block in content:
                                    if block.get("type") == "tool_result":
                                        tool_id = block.get("tool_use_id")
                                        stdout = block.get("content", "")
                                        if isinstance(stdout, list):
                                            stdout_parts = []
                                            for b in stdout:
                                                if isinstance(b, dict) and b.get("type") == "text":
                                                    stdout_parts.append(b.get("text", ""))
                                                elif isinstance(b, str):
                                                    stdout_parts.append(b)
                                            stdout = "\n".join(stdout_parts)
                                        elif not isinstance(stdout, str):
                                            stdout = str(stdout)
                                        is_error = block.get("is_error", False)
                                        
                                        if tool_id in tool_calls_map:
                                            t_call = tool_calls_map[tool_id]
                                            steps.append({
                                                "type": map_tool_name_to_step_type(t_call["name"]),
                                                "name": t_call["name"],
                                                "content": stdout,
                                                "status": "ERROR" if is_error else "OK",
                                                "resolved_args": t_call["input"]
                                            })
                            else:
                                steps.append({
                                    "type": "USER_INPUT",
                                    "content": content
                                })
                                
                    elif line_type == "assistant" and "message" in data:
                        msg = data["message"]
                        role = msg.get("role")
                        if role == "assistant":
                            blocks = msg.get("content", [])
                            text_content = []
                            thinking_content = []
                            proposed_tool_calls = []
                            
                            for block in blocks:
                                b_type = block.get("type")
                                if b_type == "text":
                                    text_content.append(block.get("text", ""))
                                elif b_type == "thinking":
                                    thinking_content.append(block.get("thinking", ""))
                                elif b_type == "tool_use":
                                    t_id = block.get("id")
                                    t_name = block.get("name")
                                    t_input = block.get("input", {})
                                    
                                    tool_calls_map[t_id] = {
                                        "name": t_name,
                                        "input": t_input
                                    }
                                    proposed_tool_calls.append({
                                        "name": t_name,
                                        "arguments": t_input
                                    })
                                    
                            steps.append({
                                "type": "PLANNER_RESPONSE",
                                "content": "\n".join(text_content),
                                "thinking": "\n".join(thinking_content),
                                "tool_calls": proposed_tool_calls
                            })
                except Exception:
                    continue
    except Exception:
        pass
    return steps


def parse_codex_jsonl(log_file: Path) -> list:
    steps = []
    tool_calls_map = {}
    try:
        with log_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    line_type = data.get("type")
                    
                    if line_type == "response_item" and "payload" in data:
                        payload = data["payload"]
                        payload_type = payload.get("type")
                        
                        if payload_type == "message":
                            role = payload.get("role")
                            content = payload.get("content", [])
                            
                            if role == "user":
                                text_parts = []
                                for block in content:
                                    if isinstance(block, dict):
                                        b_type = block.get("type")
                                        if b_type in ("input_text", "text"):
                                            text_parts.append(block.get("text", ""))
                                    elif isinstance(block, str):
                                        text_parts.append(block)
                                content_str = "\n".join(text_parts).strip()
                                if content_str:
                                    steps.append({
                                        "type": "USER_INPUT",
                                        "content": content_str
                                    })
                                    
                            elif role == "assistant":
                                text_content = []
                                thinking_content = []
                                proposed_tool_calls = []
                                
                                for block in content:
                                    if isinstance(block, dict):
                                        b_type = block.get("type")
                                        if b_type in ("text", "output_text"):
                                            text_content.append(block.get("text", ""))
                                        elif b_type == "thinking":
                                            thinking_content.append(block.get("thinking", ""))
                                    elif isinstance(block, str):
                                        text_content.append(block)
                                        
                                steps.append({
                                    "type": "PLANNER_RESPONSE",
                                    "content": "\n".join(text_content),
                                    "thinking": "\n".join(thinking_content),
                                    "tool_calls": proposed_tool_calls
                                })
                                
                        elif payload_type == "custom_tool_call":
                            call_id = payload.get("call_id")
                            name = payload.get("name")
                            t_input = payload.get("input", "")
                            tool_calls_map[call_id] = {
                                "name": name,
                                "input": t_input
                            }
                            
                        elif payload_type == "custom_tool_call_output":
                            call_id = payload.get("call_id")
                            output_blocks = payload.get("output", [])
                            
                            stdout_parts = []
                            if isinstance(output_blocks, list):
                                for block in output_blocks:
                                    if isinstance(block, dict):
                                        b_type = block.get("type")
                                        if b_type in ("input_text", "text"):
                                            stdout_parts.append(block.get("text", ""))
                                    elif isinstance(block, str):
                                        stdout_parts.append(block)
                            elif isinstance(output_blocks, str):
                                stdout_parts.append(output_blocks)
                                
                            stdout = "\n".join(stdout_parts)
                            is_error = payload.get("is_error", False)
                            
                            if call_id in tool_calls_map:
                                t_call = tool_calls_map[call_id]
                                resolved_args = t_call["input"]
                                if isinstance(resolved_args, str):
                                    resolved_args = {"script": resolved_args}
                                steps.append({
                                    "type": map_tool_name_to_step_type(t_call["name"]),
                                    "name": t_call["name"],
                                    "content": stdout,
                                    "status": "ERROR" if is_error else "OK",
                                    "resolved_args": resolved_args
                                })
                except Exception:
                    continue
    except Exception:
        pass
    return steps



class ConfigHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to suppress standard HTTP logging to keep console clean
        pass

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)
        
        # Serve transcript screenshots/media if requested
        unquoted_path = urllib.parse.unquote(path).strip("/")
        if any(x in unquoted_path for x in (".playwright-mcp", ".gemini", ".claude", ".codex")):
            if unquoted_path.startswith("home/"):
                file_path = Path("/") / unquoted_path
            else:
                file_path = Path.home() / unquoted_path
                if not file_path.exists():
                    file_path = REPO_DIR / unquoted_path

            if file_path.exists() and file_path.is_file():
                content_type = "image/png" if file_path.suffix == ".png" else "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(file_path.stat().st_size))
                self.end_headers()
                self.wfile.write(file_path.read_bytes())
                return
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"File not found")
                return
        
        # Static files serving for compiled Vite React app (frontend/dist/)
        dist_dir = REPO_DIR / "frontend" / "dist"
        
        # Resolve target file path inside dist
        rel_path = path.lstrip("/")
        if not rel_path or rel_path == "index.html":
            file_to_serve = dist_dir / "index.html"
        else:
            file_to_serve = dist_dir / rel_path
            
        # If the file exists in dist, serve it
        if dist_dir.exists() and file_to_serve.exists() and file_to_serve.is_file() and dist_dir in file_to_serve.resolve().parents:
            self.send_response(200)
            if file_to_serve.suffix == ".html":
                self.send_header("Content-Type", "text/html")
            elif file_to_serve.suffix == ".js":
                self.send_header("Content-Type", "application/javascript")
            elif file_to_serve.suffix == ".css":
                self.send_header("Content-Type", "text/css")
            elif file_to_serve.suffix == ".svg":
                self.send_header("Content-Type", "image/svg+xml")
            elif file_to_serve.suffix == ".png":
                self.send_header("Content-Type", "image/png")
            elif file_to_serve.suffix == ".json":
                self.send_header("Content-Type", "application/json")
            else:
                self.send_header("Content-Type", "application/octet-stream")
            self.end_headers()
            self.wfile.write(file_to_serve.read_bytes())
            return
            
        # SPA Fallback: Serve index.html for any non-API routes that don't map to a static file
        if not path.startswith("/api/") and dist_dir.exists() and (dist_dir / "index.html").exists():
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write((dist_dir / "index.html").read_bytes())
            return
            
        # Fallback to root index.html if dist doesn't exist and path is root
        if (path == "/" or path == "/index.html") and not dist_dir.exists():
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write((REPO_DIR / "index.html").read_bytes())
            return
            
        if path == "/api/config":
            try:
                config_data = {
                    "claude": load_claude_settings(),
                    "codex": load_codex_settings(),
                    "gemini": load_gemini_settings(),
                    "mcp_servers": get_mcp_servers(),

                    "all_mcp": get_all_mcp_servers(),
                    "disabled_mcp": load_disabled(),
                    "gemini_instructions": (REPO_DIR / "gemini" / "ANTIGRAVITY.md").read_text() if (REPO_DIR / "gemini" / "ANTIGRAVITY.md").exists() else "",
                    "claude_instructions": (REPO_DIR / "claude" / "CLAUDE.md").read_text() if (REPO_DIR / "claude" / "CLAUDE.md").exists() else "",
                    "codex_instructions": (REPO_DIR / "codex" / "AGENTS.md").read_text() if (REPO_DIR / "codex" / "AGENTS.md").exists() else "",
                    "targets": get_targets_state(),
                    "agents": list_agents(),
                    "skills": list_skills()
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(config_data).encode("utf-8"))
            except Exception as e:
                self.send_error_json(500, str(e))
                
        elif path.startswith("/api/agent/"):
            name = path.replace("/api/agent/", "")
            agent_file = AGENTS_DIR / f"{name}.md"
            if not agent_file.exists():
                self.send_error_json(404, "Agent not found")
                return
            try:
                content = agent_file.read_text()
                metadata = parse_markdown_frontmatter(agent_file)
                prompt = content
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        prompt = parts[2].strip()
                res = {"name": name, "metadata": metadata, "prompt": prompt}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(res).encode("utf-8"))
            except Exception as e:
                self.send_error_json(500, str(e))
                
        elif path.startswith("/api/skill/"):
            name = path.replace("/api/skill/", "")
            skill_file = SKILLS_DIR / name / "SKILL.md"
            if not skill_file.exists():
                self.send_error_json(404, "Skill not found")
                return
            try:
                content = skill_file.read_text()
                metadata = parse_markdown_frontmatter(skill_file)
                prompt = content
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        prompt = parts[2].strip()
                res = {"name": name, "metadata": metadata, "prompt": prompt}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(res).encode("utf-8"))
            except Exception as e:
                self.send_error_json(500, str(e))
                
        elif path == "/api/conversations":
            try:
                conversations = get_all_conversations()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(conversations, indent=2).encode("utf-8"))
            except Exception as e:
                self.send_error_json(500, str(e))
                
        elif path == "/api/analytics":
            try:
                analytics = get_aggregate_analytics()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(analytics, indent=2).encode("utf-8"))
            except Exception as e:
                self.send_error_json(500, str(e))
                
        elif path.startswith("/api/conversation/"):
            conv_id = path.replace("/api/conversation/", "")
            try:
                self.handle_get_conversation(conv_id)
            except Exception as e:
                self.send_error_json(500, str(e))

        elif path == "/api/apply/stream":
            force = query.get("force", ["false"])[0] == "true"
            claude = query.get("claude", ["true"])[0] == "true"
            codex = query.get("codex", ["true"])[0] == "true"
            agy = query.get("agy", ["true"])[0] == "true"
            
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            
            self.send_sse_line("🚀 Starting installation process...")
            args = [sys.executable, "-u", str(REPO_DIR / "install.py")]
            targets = []
            if claude: targets.append("--claude")
            if codex: targets.append("--codex")
            if agy: targets.append("--agy")
            
            if targets:
                args.extend(targets)
            else:
                args.append("--none")
                
            if force:
                args.append("--force")
                
            self.send_sse_line(f"Command: {' '.join(args)}")
            try:
                p = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                for line in iter(p.stdout.readline, ""):
                    self.send_sse_line(line.rstrip())
                p.wait()
                if p.returncode == 0:
                    self.send_sse_line("SUCCESS: ✓ Done! All changes saved and applied successfully.")
                else:
                    self.send_sse_line(f"ERROR: ✘ Apply failed with exit code {p.returncode}. Changes remain staged.")
            except Exception as e:
                self.send_sse_line(f"ERROR: ✘ Error running installer: {e}")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def handle_get_conversation(self, conv_id):
        clean_id = "".join(c for c in conv_id if c.isalnum() or c in "-_")
        parts = clean_id.split("__")
        if len(parts) < 2:
            self.send_error_json(400, "Invalid conversation ID format")
            return
            
        source = parts[0]
        steps = []
        model_name = "unknown"
        
        if source == "gemini":
            gemini_id = parts[1]
            log_file = BRAIN_DIR / gemini_id / ".system_generated" / "logs" / "transcript.jsonl"
            if not log_file.exists():
                self.send_error_json(404, "Gemini conversation log not found")
                return
            steps = parse_gemini_jsonl(log_file)
            model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
            
        elif source == "claude":
            if len(parts) < 3:
                self.send_error_json(400, "Invalid Claude conversation ID format")
                return
            project_dir_name = parts[1]
            session_id = parts[2]
            log_file = CLAUDE_DIR / project_dir_name / f"{session_id}.jsonl"
            if not log_file.exists():
                self.send_error_json(404, "Claude conversation log not found")
                return
            steps = parse_claude_jsonl(log_file)
            model_name = "claude-3-5-sonnet"
            try:
                with log_file.open("r", encoding="utf-8") as f:
                    for line in f:
                        data = json.loads(line)
                        if data.get("type") == "assistant" and "message" in data:
                            model_name = data["message"].get("model", model_name)
                            break
            except Exception:
                pass
            
        elif source == "codex":
            if len(parts) < 3:
                self.send_error_json(400, "Invalid Codex conversation ID format")
                return
            year_month_day = parts[1]
            rollout_filename = parts[2]
            
            y_m_d_parts = year_month_day.split("-")
            if len(y_m_d_parts) != 3:
                self.send_error_json(400, "Invalid Codex date format")
                return
            year, month, day = y_m_d_parts
            
            log_file = CODEX_DIR / year / month / day / f"{rollout_filename}.jsonl"
            if not log_file.exists():
                self.send_error_json(404, "Codex conversation log not found")
                return
            steps = parse_codex_jsonl(log_file)
            model_name = "gpt-5"
            try:
                with log_file.open("r", encoding="utf-8") as f:
                    for line in f:
                        data = json.loads(line)
                        if data.get("type") == "session_meta" and "payload" in data:
                            model_name = data["payload"].get("model_provider", model_name)
                            break
            except Exception:
                pass
        else:
            self.send_error_json(400, f"Unsupported conversation source: {source}")
            return

        # Determine model rates
        model_lower = model_name.lower()
        if "pro" in model_lower:
            input_rate = 1.25
            output_rate = 5.00
        elif "flash" in model_lower:
            input_rate = 0.075
            output_rate = 0.30
        elif "sonnet" in model_lower or "claude-3-5" in model_lower or "claude-3.7" in model_lower:
            input_rate = 3.00
            output_rate = 15.00
        elif "opus" in model_lower:
            input_rate = 15.00
            output_rate = 75.00
        elif "haiku" in model_lower:
            input_rate = 0.25
            output_rate = 1.25
        elif "gpt-5" in model_lower or "openai" in model_lower:
            input_rate = 5.00
            output_rate = 15.00
        else:
            input_rate = 1.25
            output_rate = 5.00

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
        
        for step in steps:
            content = step.get("content")
            if content is None:
                content = ""
            step["content"] = content
            tokens = estimate_tokens(content)
            step["est_tokens"] = tokens
            
            stats["total_steps"] += 1
            step_type = step.get("type")
            if step_type == "USER_INPUT":
                stats["user_messages"] += 1
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
                stats["est_input_tokens"] += tokens

        input_cost = (stats["est_input_tokens"] / 1_000_000.0) * input_rate
        output_cost = (stats["est_output_tokens"] / 1_000_000.0) * output_rate
        stats["est_cost"] = round(input_cost + output_cost, 4)
        
        payload = {
            "id": clean_id,
            "stats": stats,
            "steps": steps
        }
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        if path == "/api/save-temp":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                
                # 1. Save Claude
                save_claude_settings(payload.get("claude", {}))

                # 1.5. Save Gemini
                save_gemini_settings(payload.get("gemini", {}))

                # 2. Save Codex

                template_path = REPO_DIR / "codex" / "config.toml"
                codex_data = payload.get("codex", {})
                update_toml_value(template_path, None, "approval_policy", codex_data.get("approval_policy", "on-request"))
                update_toml_value(template_path, None, "sandbox_mode", codex_data.get("sandbox_mode", "workspace-write"))
                update_toml_value(template_path, None, "web_search", codex_data.get("web_search", "live"))
                update_toml_value(template_path, None, "approvals_reviewer", codex_data.get("approvals_reviewer", "user"))
                update_toml_value(template_path, None, "model", codex_data.get("model", "gpt-5.5"))
                update_toml_value(template_path, None, "model_reasoning_effort", codex_data.get("model_reasoning_effort", "medium"))
                update_toml_value(template_path, None, "persistent_instructions", codex_data.get("persistent_instructions", ""))
                
                features = codex_data.get("features", {})
                update_toml_value(template_path, "features", "memories", features.get("memories", True))
                update_toml_value(template_path, "features", "multi_agent", features.get("multi_agent", True))
                
                notice = codex_data.get("notice", {})
                update_toml_value(template_path, "notice", "hide_full_access_warning", notice.get("hide_full_access_warning", True))
                update_toml_value(template_path, "notice", "fast_default_opt_out", notice.get("fast_default_opt_out", True))

                # 3. Save disabled MCPs
                save_disabled(payload.get("disabled_mcp", []))

                # 4. Save Gemini, Claude, and Codex instructions
                (REPO_DIR / "gemini" / "ANTIGRAVITY.md").write_text(payload.get("gemini_instructions", ""))
                (REPO_DIR / "claude" / "CLAUDE.md").write_text(payload.get("claude_instructions", ""))
                (REPO_DIR / "codex" / "AGENTS.md").write_text(payload.get("codex_instructions", ""))

                # 5. Save MCP configurations directly to ~/.claude.json
                save_mcp_configs(payload.get("mcp_servers", {}), payload.get("disabled_mcp", []))

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Settings saved to templates"}).encode("utf-8"))
            except Exception as e:
                self.send_error_json(500, str(e))
        elif path == "/api/simulator/execute":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                action = payload.get("action")
                args = payload.get("args", {})
                
                if action == "view_file":
                    file_path = args.get("AbsolutePath", "")
                    resolved_path = Path(file_path).resolve()
                    if not resolved_path.exists() or not resolved_path.is_file():
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "message": f"File '{file_path}' does not exist or is not a file."}).encode("utf-8"))
                        return
                    
                    try:
                        with open(resolved_path, "r", encoding="utf-8") as f:
                            lines = [f.readline() for _ in range(15)]
                            content = "".join(lines)
                            if f.readline():
                                content += "\n... (truncated)"
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "success", "output": content}).encode("utf-8"))
                    except Exception as e:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
                
                elif action == "run_command":
                    cmd_line = args.get("CommandLine", "")
                    if not cmd_line:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "message": "Command is empty."}).encode("utf-8"))
                        return
                    
                    try:
                        proc = subprocess.run(
                            cmd_line,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            timeout=5.0,
                            cwd=str(REPO_DIR)
                        )
                        stdout_str = proc.stdout.decode("utf-8", errors="replace")
                        stderr_str = proc.stderr.decode("utf-8", errors="replace")
                        output = stdout_str + stderr_str
                        
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "status": "success" if proc.returncode == 0 else "error",
                            "output": output or "[No output generated]"
                        }).encode("utf-8"))
                    except subprocess.TimeoutExpired:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "message": "Command execution timed out (5s limit)."}).encode("utf-8"))
                    except Exception as e:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
                else:
                    self.send_response(400)
                    self.end_headers()
            except Exception as e:
                self.send_error_json(500, str(e))
        elif path == "/api/mcp/test":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                name = payload.get("name", "unknown")
                mcp_type = payload.get("type", "stdio")
                
                if mcp_type == "sse":
                    url = payload.get("url", "").strip()
                    if not url:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "message": "Error: SSE URL is empty."}).encode("utf-8"))
                        return
                    
                    try:
                        req = urllib.request.Request(url, method="GET")
                        req.add_header("User-Agent", "Mozilla/5.0 (AI Config Dashboard)")
                        with urllib.request.urlopen(req, timeout=3.0) as r:
                            self.send_response(200)
                            self.send_header("Content-Type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps({
                                "status": "success", 
                                "message": f"Successfully connected to SSE URL (HTTP {r.status})"
                            }).encode("utf-8"))
                    except Exception as conn_err:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "status": "error", 
                            "message": f"Connection failed: {conn_err}"
                        }).encode("utf-8"))
                else:
                    command = payload.get("command", "").strip()
                    if not command:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "message": "Error: Command is empty."}).encode("utf-8"))
                        return
                    
                    resolved_cmd = shutil.which(command)
                    if not resolved_cmd:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "status": "error", 
                            "message": f"Command '{command}' not found in system PATH."
                        }).encode("utf-8"))
                    else:
                        try:
                            test_args = [command]
                            if command in ["npx", "uvx", "node", "python", "python3", "pip", "npm"]:
                                test_args.append("--version")
                            
                            proc = subprocess.run(
                                test_args, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                timeout=2.0
                            )
                            version_info = proc.stdout.decode("utf-8").strip() or proc.stderr.decode("utf-8").strip()
                            version_str = f" ({version_info[:30]}...)" if version_info else ""
                            
                            self.send_response(200)
                            self.send_header("Content-Type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps({
                                "status": "success",
                                "message": f"Command '{command}' is available and executable!{version_str}"
                            }).encode("utf-8"))
                        except subprocess.TimeoutExpired:
                            self.send_response(200)
                            self.send_header("Content-Type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps({
                                "status": "success",
                                "message": f"Command '{command}' is available (launch test timed out)."
                            }).encode("utf-8"))
                        except Exception as exec_err:
                            self.send_response(200)
                            self.send_header("Content-Type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps({
                                "status": "warning",
                                "message": f"Command found at {resolved_cmd}, but execution test failed: {exec_err}"
                            }).encode("utf-8"))
            except Exception as e:
                self.send_error_json(500, str(e))
        else:
            self.send_response(404)
            self.end_headers()

    def send_sse_line(self, data: str):
        try:
            self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
            self.wfile.flush()
        except (ConnectionResetError, BrokenPipeError):
            pass

    def send_error_json(self, code: int, message: str):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"detail": message}).encode("utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Configuration Web Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the web server on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address to run the web server on")
    args = parser.parse_args()
    
    server_address = (args.host, args.port)
    httpd = ThreadingHTTPServer(server_address, ConfigHandler)
    
    print(f"Starting standard library web server on http://{args.host}:{args.port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        sys.exit(0)
