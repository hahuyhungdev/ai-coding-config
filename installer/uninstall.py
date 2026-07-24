"""Uninstallation functions for AI Coding Config."""

import json
import shutil
import subprocess
from pathlib import Path

from .cli import info, ok, warn
from .constants import CLAUDE_DIR, CODEX_DIR, GEMINI_DIR, GEMINI_CLI_DIR, REPO_DIR


def _clean_skills(target_dir: Path, label: str) -> None:
    """Helper to clean skills from target directory."""
    skills_dir = REPO_DIR / "skills"
    if skills_dir.exists():
        for d in skills_dir.iterdir():
            if d.is_dir():
                shutil.rmtree(target_dir / "skills" / d.name, ignore_errors=True)
        ok(f"Cleaned {label}")


def _clean_agents(target_dir: Path, label: str) -> None:
    """Helper to clean agents from target directory."""
    agents_dir = REPO_DIR / "agents"
    if agents_dir.exists():
        for f in agents_dir.glob("*.md"):
            (target_dir / "agents" / f.name).unlink(missing_ok=True)
        ok(f"Cleaned {label}")


def uninstall_global() -> None:
    """Uninstall all global configurations, compiled agents, skills, and command wrappers."""
    from installer_graphify import is_managed_graphify_hook
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
        _clean_skills(CLAUDE_DIR, "global skills")

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

        # Clean hooks from settings.json
        settings_path = CLAUDE_DIR / "settings.json"
        if settings_path.exists():
            try:
                data = json.loads(settings_path.read_text(encoding="utf-8"))
                if "hooks" in data and "PreToolUse" in data["hooks"]:
                    data["hooks"]["PreToolUse"] = [
                        h for h in data["hooks"]["PreToolUse"]
                        if not is_managed_graphify_hook(h)
                    ]
                    if not data["hooks"]["PreToolUse"]:
                        del data["hooks"]["PreToolUse"]
                    if not data["hooks"]:
                        del data["hooks"]
                    settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            except Exception:
                pass

        # Clean agents
        _clean_agents(CLAUDE_DIR, "global agents")

    # Clean Codex
    if CODEX_DIR.exists():
        for name in ["AGENTS.md", "RTK.md"]:
            (CODEX_DIR / name).unlink(missing_ok=True)
        # Clean skills
        _clean_skills(CODEX_DIR, "Codex skills")

    # Restore Codex binary and remove wrappers
    bin_dir = Path.home() / ".local" / "bin"
    codex_path = bin_dir / "codex"
    codex_bin = bin_dir / "codex-bin"
    if codex_bin.exists():
        try:
            if codex_path.exists() or codex_path.is_symlink():
                codex_path.unlink()
            shutil.copy2(codex_bin, codex_path)
            codex_path.chmod(0o755)
            codex_bin.unlink()
            ok("Restored original Codex binary from codex-bin")
        except Exception as e:
            warn(f"Failed to restore original Codex binary: {e}")
    else:
        codex_path.unlink(missing_ok=True)

    # Clean Gemini/agy
    if GEMINI_DIR.exists():
        for name in ["ANTIGRAVITY.md"]:
            (GEMINI_DIR / name).unlink(missing_ok=True)
        # Clean skills
        _clean_skills(GEMINI_DIR, "Gemini/agy skills")
        # Clean agents
        _clean_agents(GEMINI_DIR, "Gemini/agy agents")

    # Remove agy wrapper and installed modules while preserving user data.
    (Path.home() / ".local" / "bin" / "agy").unlink(missing_ok=True)
    (Path.home() / ".local" / "bin" / "agy.bat").unlink(missing_ok=True)

    # Clean Windows redirection wrappers
    from .setup import get_windows_home
    win_home = get_windows_home()
    if win_home:
        win_bin_dir = win_home / ".local" / "bin"
        for name in ["agy.bat", "codex.bat"]:
            p = win_bin_dir / name
            if p.exists():
                try:
                    p.unlink()
                    ok(f"Removed WSL redirection wrapper {name} from Windows")
                except Exception as e:
                    warn(f"Failed to remove Windows redirection wrapper {name}: {e}")
    agy_cli_dir = GEMINI_CLI_DIR
    agy_src_dir = REPO_DIR / "tools" / "agy"
    if agy_cli_dir.exists() and agy_src_dir.exists():
        for item in agy_src_dir.glob("*.py"):
            (agy_cli_dir / item.name).unlink(missing_ok=True)
    ok("Cleaned agy wrapper and status scripts")

    ok("Global uninstallation complete.")


def uninstall_project(project_dir: Path) -> None:
    """Uninstall project-specific configurations, hooks, instructions, and graphify graph."""
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
                if "hooks" in data:
                    for event in ["BeforeTool", "PreToolUse"]:
                        if event in data["hooks"]:
                            data["hooks"][event] = [
                                h for h in data["hooks"][event]
                                if not is_managed_graphify_hook(h)
                            ]
                            if not data["hooks"][event]:
                                del data["hooks"][event]
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
