"""Agent compilation for installer."""

from pathlib import Path
from .cli import info, run_node_script

# Directories
REPO_DIR = Path(__file__).resolve().parent.parent


def compile_agents(install_claude: bool, install_codex: bool) -> None:
    """Compile shared Markdown agents to CLI-specific formats."""
    info("Compiling custom agents...")
    flags = []
    if install_claude:
        flags.append("--claude")
    if install_codex:
        flags.append("--codex")
    run_node_script("compile-agents.js", *flags)
