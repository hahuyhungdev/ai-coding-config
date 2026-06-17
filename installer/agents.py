"""Agent compilation for installer."""

from .cli import info, run_script
from .constants import REPO_DIR


def compile_agents(install_claude: bool, install_codex: bool, install_gemini: bool = False) -> None:
    """Compile shared Markdown agents to CLI-specific formats."""
    info("Compiling custom agents...")
    flags = []
    if install_claude:
        flags.append("--claude")
    if install_codex:
        flags.append("--codex")
    if install_gemini:
        flags.append("--agy")
    run_script("compile_agents.py", *flags)

