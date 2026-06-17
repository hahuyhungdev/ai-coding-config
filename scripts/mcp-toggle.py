#!/usr/bin/env python3
"""Toggle MCP servers on/off across Claude, Codex, and Gemini configs."""

import json
import re
import shutil
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
SHARED_DISABLED = REPO_DIR / "shared-disabled-mcp.json"
CLAUDE_CONFIG = Path.home() / ".claude.json"
GEMINI_CONFIG = Path.home() / ".gemini" / "config" / "mcp_config.json"
CODEX_CONFIG = Path.home() / ".codex" / "config.toml"

GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
DIM = "\033[2m"
RESET = "\033[0m"


def load_shared_disabled():
    try:
        with open(SHARED_DISABLED) as f:
            return json.load(f).get("disabledMcpServers", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_shared_disabled(disabled_list):
    with open(SHARED_DISABLED, "w") as f:
        json.dump({"disabledMcpServers": sorted(disabled_list)}, f, indent=2)
        f.write("\n")


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_json(path, data):
    backup = path.with_suffix(path.suffix + ".bak")
    if path.exists():
        shutil.copy2(path, backup)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def sync_claude(disabled_list):
    """Sync disabled servers to Claude's ~/.claude.json."""
    if not CLAUDE_CONFIG.exists():
        return
    data = load_json(CLAUDE_CONFIG)
    enabled = data.get("mcpServers", {})
    disabled = data.get("disabledMcpServers", {})

    changed = False
    for name in disabled_list:
        if name in enabled:
            disabled[name] = enabled.pop(name)
            changed = True
    for name in list(disabled.keys()):
        if name not in disabled_list:
            enabled[name] = disabled.pop(name)
            changed = True

    data["mcpServers"] = enabled
    if disabled:
        data["disabledMcpServers"] = disabled
    elif "disabledMcpServers" in data:
        del data["disabledMcpServers"]

    if changed:
        save_json(CLAUDE_CONFIG, data)
        print(f"  {DIM}  Claude synced{RESET}")


def sync_gemini(disabled_list):
    """Sync disabled servers to Gemini's mcp_config.json."""
    if not GEMINI_CONFIG.exists():
        return
    data = load_json(GEMINI_CONFIG)
    servers = data.get("mcpServers", {})

    # Load defaults for servers that need to be re-added
    defaults = {
        "playwright": {
            "command": "npx",
            "args": ["-y", "@playwright/mcp@latest", "--browser", "msedge",
                     "--headless", "--ignore-https-errors", "--isolated",
                     "--output-dir", ".playwright-mcp"]
        },
        "context7": {
            "type": "sse",
            "url": "https://mcp.context7.com/mcp"
        },
        "memory": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"]
        },
        "sequential-thinking": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
        },
        "postgres": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-postgres",
                     "postgresql://localhost/postgres"]
        },
        "sqlite": {
            "command": "npx",
            "args": ["-y", "mcp-server-sqlite", "--db", "database.db"]
        },
        "docker": {
            "command": "npx",
            "args": ["-y", "mcp-server-docker"]
        },
        "aws": {
            "command": "uvx",
            "args": ["awslabs.aws-api-mcp-server@latest"]
        },
    }

    changed = False
    for name in disabled_list:
        if name in servers:
            del servers[name]
            changed = True
    for name in defaults:
        if name not in disabled_list and name not in servers:
            servers[name] = defaults[name]
            changed = True

    if changed:
        data["mcpServers"] = servers
        save_json(GEMINI_CONFIG, data)
        print(f"  {DIM}  Gemini synced{RESET}")


def sync_codex(disabled_list):
    """Remove disabled mcp_servers from Codex config.toml."""
    if not CODEX_CONFIG.exists():
        return
    content = CODEX_CONFIG.read_text()
    changed = False
    for name in disabled_list:
        # Remove [mcp_servers.name] section and its content
        pattern = rf'(?m)^\[mcp_servers\.{re.escape(name)}\]\n(?:.*\n)*?'
        new_content = re.sub(pattern, "", content)
        if new_content != content:
            content = new_content
            changed = True
    if changed:
        CODEX_CONFIG.write_text(content)
        print(f"  {DIM}  Codex synced{RESET}")


def list_servers():
    disabled_list = load_shared_disabled()
    data = load_json(CLAUDE_CONFIG)
    claude_enabled = set(data.get("mcpServers", {}).keys())
    claude_disabled = set(data.get("disabledMcpServers", {}).keys())
    all_names = sorted(claude_enabled | claude_disabled | set(disabled_list))

    print(f"{CYAN}MCP Servers (all CLIs):{RESET}\n")
    for name in all_names:
        if name in disabled_list:
            print(f"  {RED}✘{RESET} {name} {DIM}(disabled){RESET}")
        else:
            print(f"  {GREEN}✔{RESET} {name}")
    print()
    print(f"{DIM}Shared config: {SHARED_DISABLED}{RESET}")


def disable_server(name):
    disabled_list = load_shared_disabled()
    if name in disabled_list:
        print(f"{YELLOW}Already disabled:{RESET} {name}")
        return

    # Check server exists in at least one config
    data = load_json(CLAUDE_CONFIG)
    all_known = set(data.get("mcpServers", {}).keys()) | set(data.get("disabledMcpServers", {}).keys())
    if GEMINI_CONFIG.exists():
        gemini = load_json(GEMINI_CONFIG)
        all_known |= set(gemini.get("mcpServers", {}).keys())
    if name not in all_known:
        print(f"{RED}Error: '{name}' not found in any config.{RESET}")
        sys.exit(1)

    disabled_list.append(name)
    save_shared_disabled(disabled_list)
    sync_claude(disabled_list)
    sync_gemini(disabled_list)
    sync_codex(disabled_list)

    print(f"{YELLOW}Disabled:{RESET} {name}")
    print(f"{CYAN}Restart CLIs to apply.{RESET}")


def enable_server(name):
    disabled_list = load_shared_disabled()
    if name not in disabled_list:
        print(f"{YELLOW}Not disabled:{RESET} {name}")
        return

    disabled_list.remove(name)
    save_shared_disabled(disabled_list)
    sync_claude(disabled_list)
    sync_gemini(disabled_list)
    sync_codex(disabled_list)

    print(f"{GREEN}Enabled:{RESET} {name}")
    print(f"{CYAN}Restart CLIs to apply.{RESET}")


def enable_all():
    disabled_list = load_shared_disabled()
    if not disabled_list:
        print(f"{YELLOW}No disabled servers.{RESET}")
        return

    save_shared_disabled([])
    sync_claude([])
    sync_gemini([])
    # For codex, re-run install.py to get servers back
    print(f"{GREEN}Enabled all {len(disabled_list)} server(s).{RESET}")
    print(f"{DIM}Run install.py --codex to restore Codex MCP servers.{RESET}")


def disable_all():
    data = load_json(CLAUDE_CONFIG)
    all_names = list(data.get("mcpServers", {}).keys())
    if not all_names:
        print(f"{YELLOW}No servers to disable.{RESET}")
        return

    disabled_list = load_shared_disabled()
    for name in all_names:
        if name not in disabled_list:
            disabled_list.append(name)
    save_shared_disabled(disabled_list)
    sync_claude(disabled_list)
    sync_gemini(disabled_list)
    sync_codex(disabled_list)

    print(f"{YELLOW}Disabled all {len(disabled_list)} server(s).{RESET}")


def sync():
    """Sync disabled state from shared-disabled-mcp.json to all configs."""
    disabled_list = load_shared_disabled()
    if not disabled_list:
        print(f"{GREEN}No disabled servers in shared config.{RESET}")
        return

    print(f"{CYAN}Syncing {len(disabled_list)} disabled server(s)...{RESET}")
    sync_claude(disabled_list)
    sync_gemini(disabled_list)
    sync_codex(disabled_list)
    print(f"{GREEN}Sync complete. Restart CLIs to apply.{RESET}")


def usage():
    print(f"""Usage: mcp-toggle <command> [server-name]

Toggle MCP servers on/off across Claude, Codex, and Gemini.

Commands:
  list           List all servers with status
  enable <name>  Enable a disabled server
  disable <name> Disable a server (keeps config)
  enable-all     Enable all disabled servers
  disable-all    Disable all servers
  sync           Sync disabled state from shared-disabled-mcp.json

Examples:
  mcp-toggle list
  mcp-toggle disable aws
  mcp-toggle enable postgres
  mcp-toggle sync""")
    sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()

    cmd = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else None

    if cmd == "list":
        list_servers()
    elif cmd == "enable":
        if not arg:
            usage()
        enable_server(arg)
    elif cmd == "disable":
        if not arg:
            usage()
        disable_server(arg)
    elif cmd == "enable-all":
        enable_all()
    elif cmd == "disable-all":
        disable_all()
    elif cmd == "sync":
        sync()
    else:
        usage()
