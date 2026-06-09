"""MCP configuration for installer."""

from pathlib import Path
from .cli import info, ok, warn, run_script, run_node_script

# Directories
CLAUDE_DIR = Path.home() / ".claude"
GEMINI_DIR = Path.home() / ".gemini" / "config"
REPO_DIR = Path(__file__).resolve().parent.parent


def update_mcp_configs(install_claude: bool, install_agy: bool) -> None:
    """Update Playwright MCP configurations."""
    if not (install_claude or install_agy):
        return

    info("Ensuring Playwright MCP runs with --isolated...")

    if install_claude:
        claude_json = Path.home() / ".claude.json"
        if claude_json.exists():
            run_node_script("update-mcp-config.js", str(claude_json))

        ecc_mcp = CLAUDE_DIR / "ecc-source" / "mcp-configs" / "mcp-servers.json"
        if ecc_mcp.exists():
            run_node_script("update-mcp-config.js", str(ecc_mcp))

    if install_agy:
        gemini_mcp = GEMINI_DIR / "mcp_config.json"
        if gemini_mcp.exists():
            run_node_script("update-mcp-config.js", str(gemini_mcp))


def sync_mcp_disabled() -> None:
    """Sync disabled MCP servers from shared-disabled-mcp.json."""
    shared_disabled = REPO_DIR / "shared-disabled-mcp.json"
    if shared_disabled.exists():
        info("Syncing MCP server states...")
        run_script("mcp-toggle.py", "sync")
