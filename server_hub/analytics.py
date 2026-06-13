import json
import os
from pathlib import Path
from .constants import BRAIN_DIR, CLAUDE_DIR, CODEX_DIR
from .metadata import get_all_conversations
from .token_estimator import get_session_analytics_stats

def get_aggregate_analytics() -> dict:
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
