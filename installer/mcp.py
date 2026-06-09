"""MCP configuration for installer."""

import json
from pathlib import Path

from .cli import info, ok, warn, error
from .file_ops import merge_json

# Directories
CLAUDE_DIR = Path.home() / ".claude"
GEMINI_DIR = Path.home() / ".gemini" / "config"
REPO_DIR = Path(__file__).resolve().parent.parent


def update_mcp_configs(install_claude: bool, install_agy: bool) -> None:
    """Update MCP server configurations."""
    info("Updating MCP server configurations...")

    # Claude MCP
    if install_claude:
        source = REPO_DIR / "claude" / "mcp.json"
        target = CLAUDE_DIR / "mcp.json"
        if source.exists():
            if merge_json(source, target):
                ok("Claude MCP servers")

    # Gemini MCP
    if install_agy:
        source = REPO_DIR / "gemini" / "mcp.json"
        target = GEMINI_DIR / "mcp.json"
        if source.exists():
            if merge_json(source, target):
                ok("Gemini MCP servers")


def sync_mcp_disabled() -> None:
    """Sync disabled MCP servers."""
    info("Syncing MCP server states...")

    # Load shared disabled servers
    shared_file = REPO_DIR / "shared-disabled-mcp.json"
    if not shared_file.exists():
        return

    try:
        with open(shared_file, 'r') as f:
            shared_disabled = json.load(f)
    except Exception as e:
        warn(f"Failed to load shared disabled servers: {e}")
        return

    # Update Claude settings
    claude_settings = CLAUDE_DIR / "settings.json"
    if claude_settings.exists():
        try:
            with open(claude_settings, 'r') as f:
                settings = json.load(f)

            if 'mcpServers' in settings:
                for server_name, server_config in settings['mcpServers'].items():
                    if server_name in shared_disabled.get('claude', []):
                        server_config['disabled'] = True

            with open(claude_settings, 'w') as f:
                json.dump(settings, f, indent=2)
                f.write('\n')
        except Exception as e:
            warn(f"Failed to update Claude settings: {e}")

    # Update Gemini settings
    gemini_settings = GEMINI_DIR / "settings.json"
    if gemini_settings.exists():
        try:
            with open(gemini_settings, 'r') as f:
                settings = json.load(f)

            if 'mcpServers' in settings:
                for server_name, server_config in settings['mcpServers'].items():
                    if server_name in shared_disabled.get('gemini', []):
                        server_config['disabled'] = True

            with open(gemini_settings, 'w') as f:
                json.dump(settings, f, indent=2)
                f.write('\n')
        except Exception as e:
            warn(f"Failed to update Gemini settings: {e}")
