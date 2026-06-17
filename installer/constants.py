"""Constants for installer."""

from pathlib import Path

# Shared Directories
CLAUDE_DIR = Path.home() / ".claude"
CODEX_DIR = Path.home() / ".codex"
GEMINI_DIR = Path.home() / ".gemini" / "config"
GEMINI_CLI_DIR = Path.home() / ".gemini" / "antigravity-cli"
REPO_DIR = Path(__file__).resolve().parent.parent
