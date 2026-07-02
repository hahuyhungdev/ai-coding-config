#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Paths
REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

from backend.metadata import get_all_conversations, resolve_conversation_log
from backend.parsers import parse_gemini_jsonl, parse_claude_jsonl, parse_codex_jsonl

SKILLS_JSON_PATH = REPO_DIR / "skills.json"
SKILLS_DIR = REPO_DIR / "skills"
AGENTS_DIR = REPO_DIR / "agents"

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
    except Exception as e:
        sys.stderr.write(f"Error parsing log {log_file}: {e}\n")
    return []

def extract_invoked_subagents(step, agent_names):
    invoked = []
    tool_calls = step.get("tool_calls")
    if not tool_calls:
        return invoked
        
    if isinstance(tool_calls, str):
        try:
            tool_calls = json.loads(tool_calls)
        except Exception:
            tool_calls = []
            
    if isinstance(tool_calls, list):
        for call in tool_calls:
            if not isinstance(call, dict):
                continue
            name = str(call.get("name", ""))
            if "subagent" in name.lower() or name.lower() == "agent":
                args_str = json.dumps(call.get("args", {})).lower()
                for agent in agent_names:
                    if f'"{agent.lower()}"' in args_str or f"'{agent.lower()}'" in args_str:
                        invoked.append(agent)
                    elif agent.lower() in args_str:
                        invoked.append(agent)
    return list(set(invoked))

def main():
    # Read skills.json triggers if it exists
    registered_skills = {}
    if SKILLS_JSON_PATH.exists():
        try:
            with open(SKILLS_JSON_PATH, "r", encoding="utf-8") as f:
                skills_data = json.load(f)
                for s in skills_data.get("skills", []):
                    registered_skills[s["name"]] = s
        except Exception as e:
            sys.stderr.write(f"Error reading skills.json: {e}\n")

    # Discover all skills folders dynamically
    discovered_skills = []
    if SKILLS_DIR.exists():
        for skill_path in SKILLS_DIR.iterdir():
            if skill_path.is_dir():
                name = skill_path.name
                skill_md = skill_path / "SKILL.md"
                if not skill_md.exists():
                    continue
                
                # Check for triggers and keywords
                search_terms = [name]
                if name in registered_skills:
                    triggers = registered_skills[name].get("triggers", {})
                    keywords = triggers.get("keywords", [])
                    search_terms.extend(keywords)
                
                search_terms = sorted(list(set(search_terms)), key=len, reverse=True)
                discovered_skills.append({
                    "name": name,
                    "search_terms": search_terms,
                    "total_hits": 0,
                    "matching_conversations": {}
                })

    # Get active agents list
    agent_names = []
    if AGENTS_DIR.exists():
        for f in AGENTS_DIR.glob("*.md"):
            agent_names.append(f.stem)
    for default_agent in ["research", "self"]:
        if default_agent not in agent_names:
            agent_names.append(default_agent)

    # Get all conversations
    all_convs = get_all_conversations()
    
    # Filter for the last 30 days
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

    print(f"AI Agent & Skills Usage Analysis (Past 30 Days)")
    print(f"Total conversations found in past month: {len(monthly_convs)}\n")

    if not monthly_convs:
        print("No conversations found in the past 30 days.")
        return

    # Prepare agent list
    agents = []
    for agent_name in agent_names:
        agents.append({
            "name": agent_name,
            "total_invocations": 0,
            "matching_conversations": {}
        })

    total_steps_checked = 0
    # Process each conversation
    for conv in monthly_convs:
        steps = get_steps_for_conversation(conv)
        total_steps_checked += len(steps)
        
        # Process each step
        for step in steps:
            # Check skills
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

            for skill in discovered_skills:
                search_terms = skill["search_terms"]
                matched = [term for term in search_terms if term.lower() in combined]
                if matched:
                    skill["total_hits"] += 1
                    skill["matching_conversations"][conv["id"]] = skill["matching_conversations"].get(conv["id"], 0) + 1

            # Check subagent calls
            invoked_agents = extract_invoked_subagents(step, agent_names)
            for agent in agents:
                if agent["name"] in invoked_agents:
                    agent["total_invocations"] += 1
                    agent["matching_conversations"][conv["id"]] = agent["matching_conversations"].get(conv["id"], 0) + 1

    # Sort results
    # Sort skills by hits ascending to show the LEAST used ones
    discovered_skills.sort(key=lambda x: x["total_hits"])
    agents.sort(key=lambda x: x["total_invocations"], reverse=True)

    print(f"Checked {total_steps_checked} total steps across {len(monthly_convs)} conversations.\n")

    print(f"=== SKILLS (SORTED BY LEAST USED) ===")
    print(f"{'Skill Name':<32} | {'Total Hits':<11} | {'Convs':<6} | {'Example Conversations'}")
    print("-" * 90)
    for skill in discovered_skills:
        convs_count = len(skill["matching_conversations"])
        example_convs = []
        for conv_id, count in list(skill["matching_conversations"].items())[:2]:
            title = next((c["title"] for c in monthly_convs if c["id"] == conv_id), "Unknown")
            title_clean = title.strip().replace("\n", " ")[:30]
            example_convs.append(f"{title_clean} ({count} hits)")
        example_str = ", ".join(example_convs)
        if convs_count > 2:
            example_str += f" (+{convs_count - 2} more)"
            
        print(f"{skill['name']:<32} | {skill['total_hits']:<11} | {convs_count:<6} | {example_str if example_str else '-'}")

if __name__ == "__main__":
    main()
