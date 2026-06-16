"""Installer package for AI Coding Config."""

from .cli import info, ok, warn, error, run_script, run_node_script
from .file_ops import merge_json, copy_config, install_local_config, count_files, count_dirs
from .setup import configure_project_assistants, setup_claude, setup_codex, setup_gemini, setup_cli_wrapper, uninstall_global, uninstall_project, show_status
from .mcp import update_mcp_configs, sync_mcp_disabled
from .agents import compile_agents

__all__ = [
    # CLI
    'info', 'ok', 'warn', 'error', 'run_script', 'run_node_script',
    # File operations
    'merge_json', 'copy_config', 'install_local_config', 'count_files', 'count_dirs',
    # Setup
    'configure_project_assistants', 'setup_claude', 'setup_codex', 'setup_gemini', 'setup_cli_wrapper', 'uninstall_global', 'uninstall_project', 'show_status',
    # MCP
    'update_mcp_configs', 'sync_mcp_disabled',
    # Agents
    'compile_agents',
]
