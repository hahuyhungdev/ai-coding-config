"""Setup functions for different AI coding assistants."""

import json
import sys
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
    # Dynamic import to support unit test mocking of main install module
    # without causing circular import loops.
    install_module = sys.modules.get('install')
    
    configurators = {}
    for assistant in ["claude", "gemini", "codex"]:
        func_name = f"configure_{assistant if assistant != 'gemini' else 'gemini'}_project"
        if install_module and hasattr(install_module, func_name):
            configurators[assistant] = getattr(install_module, func_name)
        else:
            import installer_graphify
            configurators[assistant] = getattr(installer_graphify, func_name)

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
    (CLAUDE_DIR / "skills").mkdir(exist_ok=True)
    (CLAUDE_DIR / "rules" / "ecc").mkdir(parents=True, exist_ok=True)
    (CLAUDE_DIR / "hooks").mkdir(exist_ok=True)

    # CLAUDE.md
    copy_config(REPO_DIR / "claude" / "CLAUDE.md", CLAUDE_DIR / "CLAUDE.md", force)
    ok("CLAUDE.md")

    # settings.json — merge by default, overwrite with --force, but preserve Mimo/custom API keys & models
    target_settings = CLAUDE_DIR / "settings.json"
    preserved_data = {}
    if target_settings.exists():
        try:
            with open(target_settings, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if "model" in existing_data:
                    preserved_data["model"] = existing_data["model"]
                if "env" in existing_data:
                    preserved_env = {}
                    for k in ["ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "CLAUDE_CODE_OAUTH_TOKEN"]:
                        if k in existing_data["env"]:
                            preserved_env[k] = existing_data["env"][k]
                    if preserved_env:
                        preserved_data["env"] = preserved_env
        except Exception:
            pass

    if force:
        copy_config(REPO_DIR / "claude" / "settings.json", target_settings, force)
    else:
        merge_json(REPO_DIR / "claude" / "settings.json", target_settings)

    if preserved_data:
        try:
            with open(target_settings, "r", encoding="utf-8") as f:
                current_data = json.load(f)
            if "model" in preserved_data:
                current_data["model"] = preserved_data["model"]
            if "env" in preserved_data:
                if "env" not in current_data:
                    current_data["env"] = {}
                current_data["env"].update(preserved_data["env"])
            with open(target_settings, "w", encoding="utf-8") as f:
                json.dump(current_data, f, indent=2)
                f.write("\n")
        except Exception:
            pass
    ok("settings.json")

    # RTK.md
    copy_config(REPO_DIR / "claude" / "RTK.md", CLAUDE_DIR / "RTK.md", force)
    ok("RTK.md")

    # Skills
    skills_dir = REPO_DIR / "skills"
    if skills_dir.exists():
        for d in skills_dir.iterdir():
            if d.is_dir():
                copy_config(d, CLAUDE_DIR / "skills" / d.name, force)
        ok(f"Skills ({count_dirs(skills_dir)} dirs)")

    # Rules (ECC only)
    rules_dir = REPO_DIR / "claude" / "rules" / "ecc"
    if rules_dir.exists():
        for f in rules_dir.glob("*.md"):
            copy_config(f, CLAUDE_DIR / "rules" / "ecc" / f.name, force)
        ok(f"Rules ({count_files(rules_dir, '*.md')} files)")

    # Hooks
    hooks_dir = REPO_DIR / "claude" / "hooks"
    if hooks_dir.exists():
        hooks_copied = 0
        for f in hooks_dir.iterdir():
            if f.is_file():
                copy_config(f, CLAUDE_DIR / "hooks" / f.name, force)
                hooks_copied += 1
        if hooks_copied > 0:
            ok(f"Hooks ({hooks_copied} files)")


def setup_codex(force: bool) -> None:
    """Setup Codex CLI configuration."""
    info("Setting up Codex CLI...")

    CODEX_DIR.mkdir(parents=True, exist_ok=True)
    (CODEX_DIR / "agents").mkdir(exist_ok=True)
    (CODEX_DIR / "skills").mkdir(exist_ok=True)

    # AGENTS.md
    copy_config(REPO_DIR / "codex" / "AGENTS.md", CODEX_DIR / "AGENTS.md", force)
    ok("AGENTS.md")

    # RTK.md
    copy_config(REPO_DIR / "codex" / "RTK.md", CODEX_DIR / "RTK.md", force)
    ok("RTK.md")

    # config.toml
    install_local_config(REPO_DIR / "codex" / "config.toml", CODEX_DIR / "config.toml", force)
    ok("config.toml")

    # Skills
    skills_dir = REPO_DIR / "skills"
    if skills_dir.exists():
        for d in skills_dir.iterdir():
            if d.is_dir():
                copy_config(d, CODEX_DIR / "skills" / d.name, force)
        ok(f"Skills ({count_dirs(skills_dir)} dirs)")


def setup_agy(force: bool) -> None:
    """Setup Antigravity CLI (agy) configuration."""
    info("Setting up Antigravity CLI (agy)...")

    GEMINI_DIR.mkdir(parents=True, exist_ok=True)

    # Skills
    skills_target = GEMINI_DIR / "skills"
    if skills_target.is_symlink():
        warn("Skills directory is symlinked - replacing with copies")
        skills_target.unlink()

    skills_dir = REPO_DIR / "skills"
    if skills_dir.exists():
        skills_target.mkdir(exist_ok=True)
        for d in skills_dir.iterdir():
            if d.is_dir():
                copy_config(d, skills_target / d.name, force)
        ok(f"Skills ({count_dirs(skills_dir)} dirs) copied to agy config")

    # Agents
    agents_target = GEMINI_DIR / "agents"
    if agents_target.is_symlink():
        agents_target.unlink()
    agents_target.mkdir(exist_ok=True)
    ok(f"Agents ({count_files(agents_target, '*.md')} files) configured for agy")

    # ANTIGRAVITY.md
    copy_config(REPO_DIR / "gemini" / "ANTIGRAVITY.md", GEMINI_DIR / "ANTIGRAVITY.md", force)
    ok("ANTIGRAVITY.md")

    # settings.json
    agy_cli_dir = GEMINI_DIR.parent / "antigravity-cli"
    agy_cli_dir.mkdir(parents=True, exist_ok=True)
    if force:
        copy_config(REPO_DIR / "gemini" / "settings.json", agy_cli_dir / "settings.json", force)
    else:
        merge_json(REPO_DIR / "gemini" / "settings.json", agy_cli_dir / "settings.json")
    ok("settings.json")


def setup_cli_wrapper(repo_dir: Path) -> None:
    """Create a global cli wrapper named ai-config in ~/.local/bin/."""
    info("Setting up global command wrapper (ai-config)...")

    bin_dir = Path.home() / ".local" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    bash_path = bin_dir / "ai-config"
    bash_content = f"""#!/usr/bin/env bash
# Wrapper command for AI Coding Config Engine

REPO_DIR="{repo_dir.resolve()}"

if [ "$1" = "init" ]; then
    python3 "$REPO_DIR/install.py" --all --project "$PWD" --force
else
    # Forward other arguments directly to install.py
    python3 "$REPO_DIR/install.py" "$@"
fi
"""

    bat_path = bin_dir / "ai-config.bat"
    bat_content = f"""@echo off
REM Windows wrapper for AI Coding Config Engine

set REPO_DIR={repo_dir.resolve()}

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    where python3 >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] python is not found in your PATH.
        exit /b 1
    ) else (
        set PYTHON_BIN=python3
    )
) else (
    set PYTHON_BIN=python
)

if "%1"=="init" (
    %PYTHON_BIN% "%REPO_DIR%\\install.py" --all --project "%CD%" --force
) else (
    %PYTHON_BIN% "%REPO_DIR%\\install.py" %*
)
"""

    try:
        bash_path.write_text(bash_content, encoding="utf-8")
        bash_path.chmod(0o755)
        bat_path.write_text(bat_content, encoding="utf-8")
        ok("ai-config (bash & bat) wrapper commands installed to ~/.local/bin")
    except Exception as exc:
        warn(f"Failed to install ai-config wrapper command: {exc}")
