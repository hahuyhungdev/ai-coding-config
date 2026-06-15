"""Setup functions for different AI coding assistants."""

import json
import sys
from pathlib import Path
from typing import Optional

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
    %PYTHON_BIN% "%REPO_DIR%\\install.py" --all --project "%CD%" --force
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


def uninstall_global() -> None:
    """Uninstall all global configurations, compiled agents, skills, and command wrappers."""
    import shutil
    info("Uninstalling global AI Coding Config...")

    # 1. Remove global CLI wrapper
    bin_dir = Path.home() / ".local" / "bin"
    for filename in ["ai-config", "ai-config.bat"]:
        p = bin_dir / filename
        if p.exists():
            try:
                p.unlink()
                ok(f"Removed global CLI wrapper {filename}")
            except Exception as e:
                warn(f"Failed to remove {filename}: {e}")

    # 2. Clean up global Claude directory
    if CLAUDE_DIR.exists():
        # Remove copied instructions
        for name in ["CLAUDE.md", "RTK.md"]:
            p = CLAUDE_DIR / name
            if p.exists():
                p.unlink()

        # Clean skills
        skills_dir = REPO_DIR / "skills"
        if skills_dir.exists():
            for d in skills_dir.iterdir():
                if d.is_dir():
                    shutil.rmtree(CLAUDE_DIR / "skills" / d.name, ignore_errors=True)
            ok("Cleaned global skills")

        # Clean rules
        rules_dir = REPO_DIR / "claude" / "rules" / "ecc"
        if rules_dir.exists():
            for f in rules_dir.glob("*.md"):
                (CLAUDE_DIR / "rules" / "ecc" / f.name).unlink(missing_ok=True)
            ok("Cleaned global rules")

        # Clean hooks
        hooks_dir = REPO_DIR / "claude" / "hooks"
        if hooks_dir.exists():
            for f in hooks_dir.iterdir():
                (CLAUDE_DIR / "hooks" / f.name).unlink(missing_ok=True)
            ok("Cleaned global hooks")

        # Clean agents
        agents_dir = REPO_DIR / "agents"
        if agents_dir.exists():
            for f in agents_dir.glob("*.md"):
                (CLAUDE_DIR / "agents" / f.name).unlink(missing_ok=True)
            ok("Cleaned global agents")

    # Clean Codex
    if CODEX_DIR.exists():
        for name in ["AGENTS.md", "RTK.md"]:
            (CODEX_DIR / name).unlink(missing_ok=True)
        # Clean skills
        skills_dir = REPO_DIR / "skills"
        if skills_dir.exists():
            for d in skills_dir.iterdir():
                if d.is_dir():
                    shutil.rmtree(CODEX_DIR / "skills" / d.name, ignore_errors=True)
            ok("Cleaned Codex skills")

    # Clean Gemini/agy
    if GEMINI_DIR.exists():
        for name in ["ANTIGRAVITY.md"]:
            (GEMINI_DIR / name).unlink(missing_ok=True)
        # Clean skills
        skills_dir = REPO_DIR / "skills"
        if skills_dir.exists():
            for d in skills_dir.iterdir():
                if d.is_dir():
                    shutil.rmtree(GEMINI_DIR / "skills" / d.name, ignore_errors=True)
            ok("Cleaned Gemini/agy skills")
        # Clean agents
        agents_dir = REPO_DIR / "agents"
        if agents_dir.exists():
            for f in agents_dir.glob("*.md"):
                (GEMINI_DIR / "agents" / f.name).unlink(missing_ok=True)
            ok("Cleaned Gemini/agy agents")

    # Remove agy wrapper and antigravity-cli directory
    (Path.home() / ".local" / "bin" / "agy").unlink(missing_ok=True)
    (Path.home() / ".local" / "bin" / "agy.bat").unlink(missing_ok=True)
    agy_cli_dir = Path.home() / ".gemini" / "antigravity-cli"
    if agy_cli_dir.exists():
        shutil.rmtree(agy_cli_dir, ignore_errors=True)
    ok("Cleaned agy wrapper and status scripts")

    ok("Global uninstallation complete.")


def uninstall_project(project_dir: Path) -> None:
    """Uninstall project-specific configurations, hooks, instructions, and graphify graph."""
    import shutil
    import subprocess
    from installer_graphify import is_managed_graphify_hook

    info(f"Uninstalling project-level configurations from {project_dir}...")

    # 1. Uninstall Graphify git hooks
    if shutil.which("graphify"):
        try:
            subprocess.run(["graphify", "hook", "uninstall"], cwd=str(project_dir), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ok("Uninstalled Graphify git hooks")
        except Exception:
            pass

    # 2. Remove graphify-out directory
    graphify_out = project_dir / "graphify-out"
    if graphify_out.exists():
        try:
            shutil.rmtree(graphify_out)
            ok("Removed graphify-out directory")
        except Exception as e:
            warn(f"Failed to remove graphify-out: {e}")

    # 3. Clean instructions from CLAUDE.md / AGENTS.md / ANTIGRAVITY.md
    for name in ["CLAUDE.md", "AGENTS.md", "ANTIGRAVITY.md"]:
        p = project_dir / name
        if p.exists():
            try:
                content = p.read_text(encoding="utf-8")
                # Remove Graphify block
                if "<!-- ai-coding-config:graphify-start -->" in content and "<!-- ai-coding-config:graphify-end -->" in content:
                    before, remainder = content.split("<!-- ai-coding-config:graphify-start -->", 1)
                    _, after = remainder.split("<!-- ai-coding-config:graphify-end -->", 1)
                    cleaned = before.rstrip() + ("\n" if before.strip() else "") + after.lstrip()
                    if cleaned.strip():
                        p.write_text(cleaned, encoding="utf-8")
                        ok(f"Cleaned Graphify instructions from {name}")
                    else:
                        p.unlink()
                        ok(f"Removed empty instruction file {name}")
            except Exception as e:
                warn(f"Failed to clean {name}: {e}")

    # 4. Remove managed hooks from settings.json/hooks.json
    # Claude
    claude_settings = project_dir / ".claude" / "settings.json"
    if claude_settings.exists():
        try:
            data = json.loads(claude_settings.read_text(encoding="utf-8"))
            if "hooks" in data and "PreToolUse" in data["hooks"]:
                data["hooks"]["PreToolUse"] = [
                    h for h in data["hooks"]["PreToolUse"]
                    if not is_managed_graphify_hook(h)
                ]
                if not data["hooks"]["PreToolUse"]:
                    del data["hooks"]["PreToolUse"]
                if not data["hooks"]:
                    del data["hooks"]

                if data:
                    claude_settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
                    ok("Cleaned managed hooks from .claude/settings.json")
                else:
                    shutil.rmtree(claude_settings.parent, ignore_errors=True)
                    ok("Removed empty .claude directory")
        except Exception as e:
            warn(f"Failed to clean .claude/settings.json: {e}")

    # Gemini
    gemini_global_settings = Path.home() / ".gemini" / "antigravity-cli" / "settings.json"
    for settings_path in [gemini_global_settings, project_dir / ".gemini" / "settings.json"]:
        if settings_path.exists():
            try:
                data = json.loads(settings_path.read_text(encoding="utf-8"))
                if "hooks" in data and "BeforeTool" in data["hooks"]:
                    data["hooks"]["BeforeTool"] = [
                        h for h in data["hooks"]["BeforeTool"]
                        if not is_managed_graphify_hook(h)
                    ]
                    if not data["hooks"]["BeforeTool"]:
                        del data["hooks"]["BeforeTool"]
                    if not data["hooks"]:
                        del data["hooks"]

                    if data:
                        settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
                        ok(f"Cleaned managed hooks from {settings_path}")
                    else:
                        if settings_path == gemini_global_settings:
                            settings_path.unlink()
                        else:
                            shutil.rmtree(settings_path.parent, ignore_errors=True)
                        ok(f"Removed empty settings file {settings_path}")
            except Exception as e:
                warn(f"Failed to clean {settings_path}: {e}")

    # Codex
    codex_hooks = project_dir / ".codex" / "hooks.json"
    if codex_hooks.exists():
        try:
            data = json.loads(codex_hooks.read_text(encoding="utf-8"))
            if "hooks" in data and "PreToolUse" in data["hooks"]:
                data["hooks"]["PreToolUse"] = [
                    h for h in data["hooks"]["PreToolUse"]
                    if not is_managed_graphify_hook(h)
                ]
                if not data["hooks"]["PreToolUse"]:
                    del data["hooks"]["PreToolUse"]
                if not data["hooks"]:
                    del data["hooks"]

                if data:
                    codex_hooks.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
                    ok("Cleaned managed hooks from .codex/hooks.json")
                else:
                    shutil.rmtree(codex_hooks.parent, ignore_errors=True)
                    ok("Removed empty .codex directory")
        except Exception as e:
            warn(f"Failed to clean .codex/hooks.json: {e}")

    ok("Project uninstallation complete.")


def get_latest_session_tokens() -> Optional[tuple[str, int]]:
    """Helper to calculate latest session token usage."""
    import json
    brain_dir = Path.home() / ".gemini" / "antigravity-cli" / "brain"
    if not brain_dir.exists() or not brain_dir.is_dir():
        return None
    
    latest_folder = None
    latest_mtime = 0
    
    for folder in brain_dir.iterdir():
        if folder.is_dir():
            transcript_path = folder / ".system_generated" / "logs" / "transcript.jsonl"
            if transcript_path.exists():
                mtime = transcript_path.stat().st_mtime
                if mtime > latest_mtime:
                    latest_mtime = mtime
                    latest_folder = folder
                    
    if not latest_folder:
        return None
        
    transcript_path = latest_folder / ".system_generated" / "logs" / "transcript.jsonl"
    
    def estimate_tokens(text):
        if not text: return 0
        if not isinstance(text, str): text = str(text)
        chars = len(text)
        non_ascii = sum(1 for char in text if ord(char) > 127)
        return int(((chars - non_ascii) / 4.0) + (non_ascii / 1.5))

    total_input_tokens = 0
    try:
        with transcript_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    step = json.loads(line)
                    stype = step.get("type")
                    content = step.get("content") or ""
                    tokens = estimate_tokens(content)
                    if stype == "USER_INPUT":
                        total_input_tokens += 25000 + tokens
                    elif stype != "PLANNER_RESPONSE":
                        total_input_tokens += tokens
        return latest_folder.name, total_input_tokens
    except Exception:
        return None


def show_status() -> None:
    """Show configuration status, active account, and token usage."""
    import shutil
    import subprocess
    from .cli import GREEN, RED, YELLOW, BLUE, RESET
    
    info("AI Coding Config Status Check")
    print("=" * 60)
    
    # 1. Check AI Assistant Executables in PATH
    print("\n🔍 AI Assistants installation status:")
    for cli, name in [("claude", "Claude Code"), ("codex", "Codex CLI"), ("agy", "Antigravity CLI")]:
        path = shutil.which(cli)
        if path:
            print(f"  {GREEN}🟢 {name}{RESET}: Installed at {path}")
        else:
            print(f"  {RED}🔴 {name}{RESET}: Not found in $PATH")
            
    # 2. Check active Gemini/agy accounts
    print("\n👤 Active Gemini accounts (agyswap):")
    if shutil.which("agyswap") or shutil.which("agy"):
        try:
            res = subprocess.run(["agyswap", "list"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                print(res.stdout.strip())
            else:
                print("  (agyswap list failed or no accounts configured)")
        except Exception:
            print("  (Failed to query agyswap status)")
    else:
        print("  agyswap/agy not installed.")

    # 3. Check Token Budget for latest session
    print("\n🪙  Recent Gemini Token Budget & Telemetry:")
    latest_tokens = get_latest_session_tokens()
    if latest_tokens is not None:
        folder_name, tokens = latest_tokens
        print(f"  Latest session ({folder_name[:8]}): consumed {tokens:,} input tokens (Budget limit: 300,000)")
    else:
        print("  No recent Gemini session telemetry found.")

    # 4. Check Current Project Hook Status
    print("\n📁 Current directory project-level status:")
    cwd = Path.cwd()
    print(f"  Directory: {cwd}")
    
    graph_json = cwd / "graphify-out" / "graph.json"
    if graph_json.exists():
        print(f"  {GREEN}🟢 Graphify Graph{RESET}: Initialized ({graph_json.stat().st_size / 1024:.2f} KB)")
    else:
        print(f"  {YELLOW}🟡 Graphify Graph{RESET}: Not initialized in this directory")
        
    commit_hook = cwd / ".git" / "hooks" / "post-commit"
    checkout_hook = cwd / ".git" / "hooks" / "post-checkout"
    if commit_hook.exists() and checkout_hook.exists():
        print(f"  {GREEN}🟢 Git Hooks{RESET}: Graphify hooks are installed")
    else:
        print(f"  {YELLOW}🟡 Git Hooks{RESET}: Graphify hooks are NOT installed in this git repo")

    claude_settings = cwd / ".claude" / "settings.json"
    if claude_settings.exists():
        print(f"  {GREEN}🟢 Claude Hooks{RESET}: Project-level hooks configured in .claude/settings.json")
    else:
        print(f"  {YELLOW}🟡 Claude Hooks{RESET}: Project-level hooks NOT configured")

    print("\n" + "=" * 60)
