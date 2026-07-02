#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

from backend.metadata import get_all_conversations, resolve_conversation_log
from backend.parsers import parse_gemini_jsonl, parse_claude_jsonl, parse_codex_jsonl

SKILLS_JSON_PATH = REPO_DIR / "skills.json"

def get_steps_for_conversation(conv):
    conv_id = conv["id"]
    source = conv["source"]
    log_file, _ = resolve_conversation_log(conv_id)
    if not log_file or not log_file.exists():
        return []
    try:
        if source == "gemini":
            return parse_gemini_jsonl(log_file)
        elif source == "claude":
            return parse_claude_jsonl(log_file)
        elif source == "codex":
            return parse_codex_jsonl(log_file)
    except Exception:
        pass
    return []

def main():
    if not SKILLS_JSON_PATH.exists():
        print(f"Error: {SKILLS_JSON_PATH} not found.")
        return

    with open(SKILLS_JSON_PATH, "r", encoding="utf-8") as f:
        skills_data = json.load(f)

    # Get past 30 days conversations
    all_convs = get_all_conversations()
    now = datetime.now()
    one_month_ago = now - timedelta(days=30)
    
    monthly_convs = []
    for conv in all_convs:
        try:
            dt_str = conv["last_updated"].replace("Z", "+00:00")
            dt = datetime.fromisoformat(dt_str)
            dt = dt.replace(tzinfo=None)
            if dt >= one_month_ago:
                monthly_convs.append(conv)
        except Exception:
            pass

    print(f"Scanning {len(monthly_convs)} real conversations from the past month...")

    target_skills = ["react-pattern", "react-architecture", "ui-ux-design", "karpathy-guidelines", "frontend-scan", "backend-pattern", "quality-gate", "context-budget"]
    skill_stats = {name: {"hits": 0, "convs": set()} for name in target_skills}

    for conv in monthly_convs:
        steps = get_steps_for_conversation(conv)
        for step in steps:
            content = str(step.get("content") or "").lower()
            message_text = ""
            if "message" in step and isinstance(step["message"], dict):
                message_text = str(step["message"].get("content") or "")
            elif "payload" in step and isinstance(step["payload"], dict):
                payload = step["payload"]
                if "content" in payload and isinstance(payload["content"], list):
                    for block in payload["content"]:
                        if isinstance(block, dict) and "text" in block:
                            message_text += block["text"] + "\n"
            tool_calls_text = str(step.get("tool_calls") or "").lower()
            combined = (content + "\n" + message_text + "\n" + tool_calls_text).lower()

            for name in target_skills:
                skill_conf = next((s for s in skills_data.get("skills", []) if s["name"] == name), None)
                if not skill_conf:
                    continue
                keywords = [name] + skill_conf.get("triggers", {}).get("keywords", [])
                
                matched = [kw for kw in keywords if kw.lower() in combined]
                if matched:
                    skill_stats[name]["hits"] += 1
                    skill_stats[name]["convs"].add(conv["id"])

    print("\n=== TRIGGER STATUS ON REAL CONVERSATION HISTORY ===")
    print(f"{'Skill Name':<25} | {'Total Hits':<12} | {'Conversations':<15}")
    print("-" * 60)
    for name in target_skills:
        hits = skill_stats[name]["hits"]
        conv_count = len(skill_stats[name]["convs"])
        print(f"{name:<25} | {hits:<12} | {conv_count:<15}")

if __name__ == "__main__":
    main()
