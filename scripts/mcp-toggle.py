#!/usr/bin/env python3
"""Toggle MCP servers on/off across Claude, Codex, and Gemini configs."""

import sys
from pathlib import Path

# Setup sys.path appropriately so backend is importable
REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

from backend.mcp_manager import (
    load_disabled,
    save_disabled,
    get_mcp_servers,
    save_mcp_configs,
)
from backend.constants import SHARED_DISABLED

GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
DIM = "\033[2m"
RESET = "\033[0m"


def list_servers():
    disabled_list = load_disabled()
    configs = get_mcp_servers()
    all_names = sorted(set(configs.keys()) | set(disabled_list))

    print(f"{CYAN}MCP Servers (all CLIs):{RESET}\n")
    for name in all_names:
        if name in disabled_list:
            print(f"  {RED}✘{RESET} {name} {DIM}(disabled){RESET}")
        else:
            print(f"  {GREEN}✔{RESET} {name}")
    print()
    print(f"{DIM}Shared config: {SHARED_DISABLED}{RESET}")


def disable_server(name):
    disabled_list = load_disabled()
    if name in disabled_list:
        print(f"{YELLOW}Already disabled:{RESET} {name}")
        return

    # Check server exists
    configs = get_mcp_servers()
    if name not in configs:
        print(f"{RED}Error: '{name}' not found in any config.{RESET}")
        sys.exit(1)

    disabled_list.append(name)
    save_disabled(disabled_list)
    save_mcp_configs(configs, disabled_list)

    print(f"{YELLOW}Disabled:{RESET} {name}")
    print(f"{CYAN}Restart CLIs to apply.{RESET}")


def enable_server(name):
    disabled_list = load_disabled()
    if name not in disabled_list:
        print(f"{YELLOW}Not disabled:{RESET} {name}")
        return

    disabled_list.remove(name)
    save_disabled(disabled_list)
    
    configs = get_mcp_servers()
    save_mcp_configs(configs, disabled_list)

    print(f"{GREEN}Enabled:{RESET} {name}")
    print(f"{CYAN}Restart CLIs to apply.{RESET}")


def enable_all():
    disabled_list = load_disabled()
    if not disabled_list:
        print(f"{YELLOW}No disabled servers.{RESET}")
        return

    save_disabled([])
    configs = get_mcp_servers()
    save_mcp_configs(configs, [])
    
    print(f"{GREEN}Enabled all {len(disabled_list)} server(s).{RESET}")
    print(f"{DIM}Run install.py --codex to restore Codex MCP servers.{RESET}")


def disable_all():
    configs = get_mcp_servers()
    all_names = list(configs.keys())
    if not all_names:
        print(f"{YELLOW}No servers to disable.{RESET}")
        return

    disabled_list = load_disabled()
    for name in all_names:
        if name not in disabled_list:
            disabled_list.append(name)
            
    save_disabled(disabled_list)
    save_mcp_configs(configs, disabled_list)

    print(f"{YELLOW}Disabled all {len(disabled_list)} server(s).{RESET}")


def sync():
    """Sync disabled state from shared-disabled-mcp.json to all configs."""
    disabled_list = load_disabled()
    if not disabled_list:
        print(f"{GREEN}No disabled servers in shared config.{RESET}")
        return

    print(f"{CYAN}Syncing {len(disabled_list)} disabled server(s)...{RESET}")
    configs = get_mcp_servers()
    save_mcp_configs(configs, disabled_list)
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
