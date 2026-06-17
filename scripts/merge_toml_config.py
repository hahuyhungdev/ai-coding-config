#!/usr/bin/env python3
import sys
import json
import re
from pathlib import Path

def parse_toml(content: str) -> dict:
    lines = content.splitlines()
    root = {}
    current_table = None

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        table_match = re.match(r"^\[([^\]]+)\]$", line)
        if table_match:
            current_table = table_match.group(1).strip()
            if current_table not in root:
                root[current_table] = {}
            continue

        kv_match = re.match(r"^([^=]+)=\s*(.+)$", line)
        if kv_match:
            key = kv_match.group(1).strip()
            val = kv_match.group(2).strip()
            if current_table:
                root[current_table][key] = val
            else:
                root[key] = val
    return root


def stringify_toml(obj: dict) -> str:
    result = []
    
    # First write top-level primitive keys
    for key, val in obj.items():
        if not isinstance(val, dict):
            result.append(f"{key} = {val}")
    result.append("")

    # Then write tables
    for key, val in obj.items():
        if isinstance(val, dict):
            result.append(f"[{key}]")
            for sub_key, sub_val in val.items():
                result.append(f"{sub_key} = {sub_val}")
            result.append("")
            
    return "\n".join(result) + "\n"


def main():
    if len(sys.argv) < 3:
        print("Usage: python merge_toml_config.py <source-config> <target-config>", file=sys.stderr)
        sys.exit(1)

    repo_config_path = Path(sys.argv[1])
    user_config_path = Path(sys.argv[2])

    # Read shared disabled list
    shared_disabled_path = Path(__file__).resolve().parent.parent / "shared-disabled-mcp.json"
    shared_disabled = []
    if shared_disabled_path.exists():
        try:
            shared = json.loads(shared_disabled_path.read_text(encoding="utf-8"))
            shared_disabled = shared.get("disabledMcpServers", [])
        except Exception:
            pass

    try:
        repo_content = repo_config_path.read_text(encoding="utf-8")
        user_content = user_config_path.read_text(encoding="utf-8")

        repo_obj = parse_toml(repo_content)
        user_obj = parse_toml(user_content)

        merged_obj = dict(user_obj)

        # Remove disabled mcp_servers from both repo and user configs
        for name in shared_disabled:
            server_key = f"mcp_servers.{name}"
            repo_obj.pop(server_key, None)
            merged_obj.pop(server_key, None)

        # Remove URL-based mcp_servers from repo (Codex only supports stdio)
        for key in list(repo_obj.keys()):
            if key.startswith("mcp_servers.") and isinstance(repo_obj[key], dict) and "url" in repo_obj[key]:
                repo_obj.pop(key, None)

        # Clean up agents in user config that are no longer registered in repo config
        for key in list(merged_obj.keys()):
            if key.startswith("agents.") and key not in repo_obj:
                merged_obj.pop(key, None)

        for key, val in repo_obj.items():
            if isinstance(val, dict):
                if key not in merged_obj:
                    merged_obj[key] = dict(val)
                else:
                    if key == "mcp_servers" or key.startswith("mcp_servers."):
                        # For mcp_servers, we always prefer repo's definition to fix broken/outdated command/args
                        merged_obj[key] = {**merged_obj[key], **val}
                    else:
                        # Merge keys inside table, preferring user's existing keys
                        merged_obj[key] = {**val, **merged_obj[key]}
            else:
                if key not in merged_obj:
                    merged_obj[key] = val

        merged_content = stringify_toml(merged_obj)
        user_config_path.write_text(merged_content, encoding="utf-8")
        print(f"Successfully merged Codex configuration into {user_config_path}")
    except Exception as err:
        print(f"Failed to merge Codex config: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
