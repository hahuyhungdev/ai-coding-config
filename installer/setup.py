"""Setup functions for different AI coding assistants."""

import json
import sys
from pathlib import Path

from .cli import info, ok, warn
from .constants import CLAUDE_DIR, CODEX_DIR, GEMINI_DIR, REPO_DIR
from .file_ops import copy_config, merge_json, install_local_config, count_files, count_dirs


def _copy_skills(target_dir: Path, force: bool) -> None:
    """Helper to copy skills from repository to target directory."""
    skills_dir = REPO_DIR / "skills"
    if skills_dir.exists():
        for d in skills_dir.iterdir():
            if d.is_dir():
                copy_config(d, target_dir / "skills" / d.name, force)
        ok(f"Skills ({count_dirs(skills_dir)} dirs)")


def configure_project_assistants(project_dir: Path, assistants: list[str]) -> dict[str, bool]:
    """Configure project-level assistants."""
    # Dynamic import to support unit test mocking of main install module
    # without causing circular import loops.
    install_module = sys.modules.get('install')
    
    configurators = {}
    for assistant in ["claude", "gemini", "codex", "copilot"]:
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
            display_name = "Copilot" if assistant == "copilot" else assistant.title()
            ok(f"{display_name} project-level config configured")
            results[assistant] = True
        except Exception as exc:
            warn(f"Failed to configure {assistant} project config: {exc}")
            results[assistant] = False
    return results


def ensure_claude_rtk_hook(settings_path: Path) -> None:
    """Ensure Claude Code has the RTK Bash hook without disturbing other hooks."""
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
    except Exception:
        data = {}

    hooks = data.setdefault("hooks", {})
    pre_tool_hooks = hooks.setdefault("PreToolUse", [])
    for hook in pre_tool_hooks:
        if hook.get("matcher") != "Bash":
            continue
        for command in hook.get("hooks", []):
            if command.get("type") == "command" and command.get("command") == "rtk hook claude":
                settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
                return

    pre_tool_hooks.append({
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": "rtk hook claude"}],
    })
    settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def ensure_codex_rtk_reference(agents_path: Path, rtk_path: Path) -> None:
    """Ensure Codex global instructions include the installed RTK reference."""
    reference = f"@{rtk_path}"
    content = agents_path.read_text(encoding="utf-8") if agents_path.exists() else ""
    if reference in content:
        return
    stripped = content.rstrip()
    next_content = f"{stripped}\n\n{reference}\n" if stripped else f"{reference}\n"
    agents_path.write_text(next_content, encoding="utf-8")


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
                    for k in ["ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_AUTH_TOKEN"]:
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
    ensure_claude_rtk_hook(target_settings)
    ok("settings.json")

    # RTK.md
    copy_config(REPO_DIR / "claude" / "RTK.md", CLAUDE_DIR / "RTK.md", force)
    ok("RTK.md")

    # Skills
    _copy_skills(CLAUDE_DIR, force)

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
    ensure_codex_rtk_reference(CODEX_DIR / "AGENTS.md", CODEX_DIR / "RTK.md")

    # config.toml
    install_local_config(REPO_DIR / "codex" / "config.toml", CODEX_DIR / "config.toml", force)
    ok("config.toml")

    # Skills
    _copy_skills(CODEX_DIR, force)


def setup_gemini(force: bool) -> None:
    """Setup Gemini (Antigravity CLI) configuration."""
    info("Setting up Gemini/Antigravity configuration...")

    # Create directories
    GEMINI_DIR.mkdir(parents=True, exist_ok=True)
    (GEMINI_DIR / "agents").mkdir(exist_ok=True)
    (GEMINI_DIR / "skills").mkdir(exist_ok=True)

    # ANTIGRAVITY.md
    copy_config(REPO_DIR / "gemini" / "ANTIGRAVITY.md", GEMINI_DIR / "ANTIGRAVITY.md", force)
    ok("ANTIGRAVITY.md")

    # Skills
    _copy_skills(GEMINI_DIR, force)


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
    if [ "$2" = "ai" ]; then
        python3 "$REPO_DIR/install.py" --init-ai --project "$PWD" --backend gemini-cli "${{@:3}}"
    else
        python3 "$REPO_DIR/install.py" --all --project "$PWD" --force
    fi
elif [ "$1" = "init-ai" ]; then
    python3 "$REPO_DIR/install.py" --init-ai --project "$PWD" "${{@:2}}"
elif [ "$1" = "uninstall" ]; then
    python3 "$REPO_DIR/install.py" --uninstall --project "$PWD"
elif [ "$1" = "status" ]; then
    python3 "$REPO_DIR/install.py" --status
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
    if "%2"=="ai" (
        shift
        %PYTHON_BIN% "%REPO_DIR%\\install.py" --init-ai --project "%CD%" --backend gemini-cli %2 %3 %4 %5 %6 %7 %8 %9
    ) else (
        %PYTHON_BIN% "%REPO_DIR%\\install.py" --all --project "%CD%" --force
    )
) else if "%1"=="init-ai" (
    shift
    %PYTHON_BIN% "%REPO_DIR%\\install.py" --init-ai --project "%CD%" %1 %2 %3 %4 %5 %6 %7 %8 %9
) else if "%1"=="uninstall" (
    %PYTHON_BIN% "%REPO_DIR%\\install.py" --uninstall --project "%CD%"
) else if "%1"=="status" (
    %PYTHON_BIN% "%REPO_DIR%\\install.py" --status
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
