import json
from pathlib import Path
from .constants import ANALYTICS_CACHE
from .parsers import parse_gemini_jsonl, parse_claude_jsonl, parse_codex_jsonl, map_tool_name_to_step_type

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

def get_model_rates(model_name: str) -> tuple[float, float]:
    """Retrieve input/output pricing rates per 1M tokens for a given model."""
    model_lower = model_name.lower()
    if "flash" in model_lower:
        return 0.075, 0.30
    elif "pro" in model_lower:
        return 1.25, 5.00
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

def calculate_session_stats(steps: list, model_name: str) -> dict:
    """Calculate token usage and cost stats for a list of steps, enriching steps with est_tokens."""
    input_rate, output_rate = get_model_rates(model_name)
    
    total_steps = 0
    user_messages = 0
    tool_calls = 0
    est_input_tokens = 0
    est_output_tokens = 0
    
    for step in steps:
        content = step.get("content")
        if content is None:
            content = ""
        step["content"] = content
        tokens = estimate_tokens(content)
        step["est_tokens"] = tokens
        
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
    
    return {
        # Keys for handler.py
        "total_steps": total_steps,
        "user_messages": user_messages,
        "tool_calls": tool_calls,
        "est_input_tokens": est_input_tokens,
        "est_output_tokens": est_output_tokens,
        "est_cost": est_cost,
        "model_name": model_name,
        "input_rate": input_rate,
        "output_rate": output_rate,
        # Keys for analytics.py / get_session_analytics_stats
        "steps": total_steps,
        "turns": user_messages,
        "input_tokens": est_input_tokens,
        "output_tokens": est_output_tokens,
        "total_tokens": est_input_tokens + est_output_tokens,
        "cost": est_cost,
    }

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
        
    stats = calculate_session_stats(steps, model_name)
    
    # Prune extra keys from calculate_session_stats to keep cache clean
    analytics_stats = {
        "steps": stats["steps"],
        "turns": stats["turns"],
        "tool_calls": stats["tool_calls"],
        "input_tokens": stats["input_tokens"],
        "output_tokens": stats["output_tokens"],
        "total_tokens": stats["total_tokens"],
        "cost": stats["cost"],
        "model_name": stats["model_name"]
    }
    
    ANALYTICS_CACHE[cache_key] = analytics_stats
    return analytics_stats

