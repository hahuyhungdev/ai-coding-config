"""Setup functions for different AI coding assistants."""

from pathlib import Path

from .cli import info, ok, warn, error
from .file_ops import copy_config, merge_json, install_local_config, count_files, count_dirs

# Directories
CLAUDE_DIR = Path.home() / ".claude"
CODEX_DIR = Path.home() / ".codex"
GEMINI_DIR = Path.home() / ".gemini" / "config"
REPO_DIR = Path(__file__).resolve().parent.parent


def configure_project_assistants(project_dir: Path, assistants: list[str]) -> dict[str, bool]:
    """Configure project-level assistants."""
    from installer_graphify import (
        configure_claude_project,
        configure_codex_project,
        configure_gemini_project,
    )

    configurators = {
        "claude": configure_claude_project,
        "gemini": configure_gemini_project,
        "codex": configure_codex_project,
    }
    results = {}
    for assistant in assistants:
        try:
            configurators[assistant](project_dir)
            ok(f"{assistant.title()} project-level hook configured")
            results[assistant] = True
        except Exception as exc:
            warn(f"Failed to configure {assistant} project hooks: {exc}")
            results[assistant] = False
    return results


def setup_claude(force: bool) -> None:
    """Setup Claude Code configuration."""
    info("Setting up Claude Code...")

    # Create directories
    CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
    (CLAUDE_DIR / "agents").mkdir(exist_ok=True)
    (CLAUDE_DIR / "commands").mkdir(exist_ok=True)

    # Copy settings
    source = REPO_DIR / "claude" / "settings.json"
    target = CLAUDE_DIR / "settings.json"
    if copy_config(source, target, force):
        ok("settings.json")

    # Copy agents
    agents_source = REPO_DIR / "claude" / "agents"
    agents_target = CLAUDE_DIR / "agents"
    if copy_config(agents_source, agents_target, force):
        ok(f"Agents ({count_files(agents_target, '*.json')} files)")

    # Copy commands
    commands_source = REPO_DIR / "claude" / "commands"
    commands_target = CLAUDE_DIR / "commands"
    if copy_config(commands_source, commands_target, force):
        ok(f"Commands ({count_files(commands_target, '*.json')} files)")

    # Copy skills
    skills_source = REPO_DIR / "skills"
    skills_target = CLAUDE_DIR / "skills"
    if copy_config(skills_source, skills_target, force):
        ok(f"Skills ({count_dirs(skills_target)} dirs)")

    # Copy rules
    rules_source = REPO_DIR / "claude" / "rules"
    rules_target = CLAUDE_DIR / "rules"
    if copy_config(rules_source, rules_target, force):
        ok(f"Rules ({count_files(rules_target, '*.md')} files)")

    # Copy RTK.md
    rtk_source = REPO_DIR / "RTK.md"
    rtk_target = CLAUDE_DIR / "RTK.md"
    if copy_config(rtk_source, rtk_target, force):
        ok("RTK.md")


def setup_codex(force: bool) -> None:
    """Setup Codex CLI configuration."""
    info("Setting up Codex CLI...")

    # Create directory
    CODEX_DIR.mkdir(parents=True, exist_ok=True)

    # Copy settings
    source = REPO_DIR / "codex" / "config.toml"
    target = CODEX_DIR / "config.toml"
    if copy_config(source, target, force):
        ok("config.toml")


def setup_agy(force: bool) -> None:
    """Setup Antigravity CLI configuration."""
    info("Setting up Antigravity CLI...")

    # Create directory
    GEMINI_DIR.mkdir(parents=True, exist_ok=True)

    # Copy settings
    source = REPO_DIR / "gemini" / "settings.json"
    target = GEMINI_DIR / "settings.json"
    if copy_config(source, target, force):
        ok("settings.json")
