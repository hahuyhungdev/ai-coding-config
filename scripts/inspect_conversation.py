#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

from server_hub.constants import BRAIN_DIR
from server_hub.handler import describe_gemini_transcript_source, resolve_gemini_transcript_path
from server_hub.parsers import parse_gemini_jsonl


def _clean_conversation_id(conversation_id):
    return "".join(c for c in conversation_id if c.isalnum() or c in "-_")


def _content_preview(content, limit=240):
    if len(content) <= limit:
        return content
    return content[:limit] + "..."


def inspect_conversation(conversation_id, brain_dir=BRAIN_DIR, step_index=None, keyword=None):
    clean_id = _clean_conversation_id(conversation_id)
    parts = clean_id.split("__")
    if len(parts) < 2:
        raise ValueError("Invalid conversation ID format")
    if parts[0] != "gemini":
        raise ValueError("Only gemini conversation IDs are supported")

    gemini_id = parts[1]
    log_file = resolve_gemini_transcript_path(gemini_id, brain_dir=brain_dir)
    if log_file is None:
        raise FileNotFoundError("Gemini conversation log not found")

    steps = parse_gemini_jsonl(log_file)
    result = {
        "id": clean_id,
        "source": "gemini",
        "log_source": describe_gemini_transcript_source(gemini_id, brain_dir=brain_dir),
        "total_steps": len(steps),
    }

    if step_index is not None:
        if step_index < 0 or step_index >= len(steps):
            result["step"] = {
                "index": step_index,
                "error": f"step index out of range; total_steps={len(steps)}",
            }
        else:
            step = steps[step_index]
            content = str(step.get("content") or "")
            result["step"] = {
                "index": step_index,
                "type": step.get("type"),
                "name": step.get("name"),
                "content_length": len(content),
                "preview": _content_preview(content),
            }

    if keyword:
        hits = []
        for index, step in enumerate(steps):
            content = str(step.get("content") or "")
            if keyword in content:
                hits.append({
                    "index": index,
                    "type": step.get("type"),
                    "content_length": len(content),
                })
        result["keyword"] = {
            "query": keyword,
            "found": bool(hits),
            "hit_count": len(hits),
            "first_hits": hits[:10],
        }

    return result


def main():
    parser = argparse.ArgumentParser(description="Inspect a conversation log without ad hoc scratch scripts.")
    parser.add_argument("conversation_id", help="Conversation ID, for example gemini__<session-id>")
    parser.add_argument("--step-index", type=int, help="Optional raw transcript step index to inspect")
    parser.add_argument("--keyword", help="Optional keyword to locate in parsed step content")
    args = parser.parse_args()

    try:
        result = inspect_conversation(args.conversation_id, step_index=args.step_index, keyword=args.keyword)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
