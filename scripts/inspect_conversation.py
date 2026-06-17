#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

from server_hub.constants import BRAIN_DIR, CLAUDE_DIR, CODEX_DIR
from server_hub.metadata import describe_gemini_transcript_source, resolve_gemini_transcript_path
from server_hub.parsers import parse_gemini_jsonl, parse_claude_jsonl, parse_codex_jsonl


def _clean_conversation_id(conversation_id):
    return "".join(c for c in conversation_id if c.isalnum() or c in "-_")


def _content_preview(content, limit=240):
    if len(content) <= limit:
        return content
    return content[:limit] + "..."


def _log_path(gemini_id, brain_dir, filename):
    return brain_dir / gemini_id / ".system_generated" / "logs" / filename


def _keyword_hits(steps, keyword):
    hits = []
    for index, step in enumerate(steps):
        content = str(step.get("content") or "")
        if keyword in content:
            hits.append({
                "index": index,
                "type": step.get("type"),
                "content_length": len(content),
            })
    return hits


def _step_summary(steps, step_index):
    if step_index is None:
        return None
    if step_index < 0 or step_index >= len(steps):
        return {
            "index": step_index,
            "error": f"step index out of range; total_steps={len(steps)}",
        }
    step = steps[step_index]
    content = str(step.get("content") or "")
    return {
        "index": step_index,
        "type": step.get("type"),
        "name": step.get("name"),
        "content_length": len(content),
        "preview": _content_preview(content),
    }


def _log_summary(gemini_id, brain_dir, filename, step_index=None, keyword=None):
    log_file = _log_path(gemini_id, brain_dir, filename)
    if not log_file.exists():
        return {
            "exists": False,
            "filename": filename,
            "total_steps": 0,
        }

    steps = parse_gemini_jsonl(log_file)
    summary = {
        "exists": True,
        "filename": filename,
        "total_steps": len(steps),
    }
    step = _step_summary(steps, step_index)
    if step is not None:
        summary["step"] = step
    if keyword:
        hits = _keyword_hits(steps, keyword)
        summary["keyword"] = {
            "query": keyword,
            "found": bool(hits),
            "hit_count": len(hits),
            "first_hits": hits[:10],
        }
    return summary


def _compare_logs(gemini_id, brain_dir, step_index=None, keyword=None):
    compact = _log_summary(gemini_id, brain_dir, "transcript.jsonl", step_index, keyword)
    full = _log_summary(gemini_id, brain_dir, "transcript_full.jsonl", step_index, keyword)
    comparison = {
        "compact": compact,
        "full": full,
    }

    if step_index is not None and compact["exists"] and full["exists"]:
        compact_step = compact.get("step", {})
        full_step = full.get("step", {})
        if "error" not in compact_step and "error" not in full_step:
            compact_steps = parse_gemini_jsonl(_log_path(gemini_id, brain_dir, "transcript.jsonl"))
            full_steps = parse_gemini_jsonl(_log_path(gemini_id, brain_dir, "transcript_full.jsonl"))
            compact_content = str(compact_steps[step_index].get("content") or "")
            full_content = str(full_steps[step_index].get("content") or "")
            comparison["step"] = {
                "index": step_index,
                "same_type": compact_step.get("type") == full_step.get("type"),
                "same_content": compact_content == full_content,
                "compact": compact_step,
                "full": full_step,
            }
    return comparison


def inspect_conversation(conversation_id, brain_dir=BRAIN_DIR, claude_dir=CLAUDE_DIR, codex_dir=CODEX_DIR, step_index=None, keyword=None, compare_logs=False):
    clean_id = _clean_conversation_id(conversation_id)
    parts = clean_id.split("__")
    if len(parts) < 2:
        raise ValueError("Invalid conversation ID format")
    
    source = parts[0]
    if source not in ("gemini", "claude", "codex"):
        raise ValueError(f"Unsupported conversation source: {source}")

    if source == "gemini":
        gemini_id = parts[1]
        log_file = resolve_gemini_transcript_path(gemini_id, brain_dir=brain_dir)
        if log_file is None:
            raise FileNotFoundError("Gemini conversation log not found")
        steps = parse_gemini_jsonl(log_file)
        log_source = describe_gemini_transcript_source(gemini_id, brain_dir=brain_dir)
    elif source == "claude":
        if len(parts) < 3:
            raise ValueError("Invalid Claude conversation ID format")
        project_dir_name = parts[1]
        session_id = parts[2]
        log_file = Path(claude_dir) / project_dir_name / f"{session_id}.jsonl"
        if not log_file.exists():
            raise FileNotFoundError(f"Claude conversation log not found at {log_file}")
        steps = parse_claude_jsonl(log_file)
        log_source = {
            "kind": "standard",
            "filename": log_file.name,
            "relative_path": f"{project_dir_name}/{log_file.name}"
        }
    elif source == "codex":
        if len(parts) < 3:
            raise ValueError("Invalid Codex conversation ID format")
        year_month_day = parts[1]
        rollout_filename = parts[2]
        y_m_d_parts = year_month_day.split("-")
        if len(y_m_d_parts) != 3:
            raise ValueError("Invalid Codex date format")
        year, month, day = y_m_d_parts
        log_file = Path(codex_dir) / year / month / day / f"{rollout_filename}.jsonl"
        if not log_file.exists():
            raise FileNotFoundError(f"Codex conversation log not found at {log_file}")
        steps = parse_codex_jsonl(log_file)
        log_source = {
            "kind": "standard",
            "filename": log_file.name,
            "relative_path": f"{year}/{month}/{day}/{log_file.name}"
        }

    result = {
        "id": clean_id,
        "source": source,
        "log_source": log_source,
        "total_steps": len(steps),
    }

    if step_index is not None:
        result["step"] = _step_summary(steps, step_index)

    if keyword:
        hits = _keyword_hits(steps, keyword)
        result["keyword"] = {
            "query": keyword,
            "found": bool(hits),
            "hit_count": len(hits),
            "first_hits": hits[:10],
        }

    if compare_logs:
        if source != "gemini":
            raise ValueError("Log comparison is only supported for Gemini conversations")
        result["log_comparison"] = _compare_logs(parts[1], brain_dir, step_index, keyword)

    return result


def main():
    parser = argparse.ArgumentParser(description="Inspect a conversation log without ad hoc scratch scripts.")
    parser.add_argument("conversation_id", help="Conversation ID, for example gemini__<session-id>")
    parser.add_argument("--step-index", type=int, help="Optional raw transcript step index to inspect")
    parser.add_argument("--keyword", help="Optional keyword to locate in parsed step content")
    parser.add_argument("--compare-logs", action="store_true", help="Compare transcript.jsonl and transcript_full.jsonl without scratch scripts")
    args = parser.parse_args()

    try:
        result = inspect_conversation(
            args.conversation_id,
            step_index=args.step_index,
            keyword=args.keyword,
            compare_logs=args.compare_logs,
        )
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
