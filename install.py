#!/usr/bin/env python3
"""AI Coding Config Installer.

Copies shared Claude/Codex/Gemini assets from this repo to their expected locations.
Detects conflicts and lets user decide: overwrite, keep, or skip.
"""

import argparse
import filecmp
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from installer_graphify import (
    GRAPHIFY_INSTRUCTIONS,
    classify_graphify_tool_use,
    configure_claude_project,
    configure_codex_project,
    configure_gemini_project,
    is_broad_discovery_command,
    is_managed_graphify_hook,
    managed_claude_hooks,
)

# Colors
GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
DIM = "\033[2m"
RESET = "\033[0m"

REPO_DIR = Path(__file__).resolve().parent
CLAUDE_DIR = Path.home() / ".claude"
CODEX_DIR = Path.home() / ".codex"
GEMINI_DIR = Path.home() / ".gemini" / "config"

def configure_project_assistants(project_dir: Path, assistants: list[str]) -> dict[str, bool]:
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


def info(msg: str) -> None:
    print(f"{BLUE}[INFO]{RESET} {msg}")


def ok(msg: str) -> None:
    print(f"{GREEN}[OK]{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}[WARN]{RESET} {msg}")


def error(msg: str) -> None:
    print(f"{RED}[ERROR]{RESET} {msg}")


def run_script(script: str, *args: str) -> bool:
    """Run a script from the scripts directory."""
    script_path = REPO_DIR / "scripts" / script
    if not script_path.exists():
        warn(f"Script not found: {script}")
        return False
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), *args],
            capture_output=True,
            text=True,
        )
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return result.returncode == 0
    except Exception as e:
        warn(f"Failed to run {script}: {e}")
        return False


def run_node_script(script: str, *args: str) -> bool:
    """Run a Node.js script from the scripts directory."""
    script_path = REPO_DIR / "scripts" / script
    if not script_path.exists():
        warn(f"Script not found: {script}")
        return False
    try:
        result = subprocess.run(
            ["node", str(script_path), *args],
            capture_output=True,
            text=True,
        )
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return result.returncode == 0
    except Exception as e:
        warn(f"Failed to run {script}: {e}")
        return False


def merge_json(source: Path, target: Path) -> bool:
    """Deep-merge JSON: repo keys are base, target-only keys are preserved.

    Returns True if merged/written, False if skipped.
    """
    if not source.exists():
        warn(f"Source does not exist: {source}")
        return False

    import json

    with open(source) as f:
        repo = json.load(f)

    if not target.exists():
        with open(target, "w") as f:
            json.dump(repo, f, indent=2)
            f.write("\n")
        return True

    with open(target) as f:
        existing = json.load(f)

    def deep_merge(base: dict, override: dict) -> dict:
        merged = dict(base)
        for k, v in override.items():
            if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
                merged[k] = deep_merge(merged[k], v)
            else:
                merged[k] = v
        return merged

    merged = deep_merge(repo, existing)

    with open(target, "w") as f:
        json.dump(merged, f, indent=2)
        f.write("\n")
    return True


def copy_config(source: Path, target: Path, force: bool = False) -> bool:
    """Copy config from repo to global with conflict detection.

    Returns True if copied, False if skipped.
    """
    if not source.exists():
        warn(f"Source does not exist: {source}")
        return False

    # Remove old symlink (from previous installs)
    if target.is_symlink():
        target.unlink()

    # Target doesn't exist → copy directly
    if not target.exists():
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
        return True

    # Target exists → check for differences
    is_same = False
    if source.is_dir() and target.is_dir():
        # Compare directories recursively
        dircmp = filecmp.dircmp(source, target)
        is_same = not dircmp.left_only and not dircmp.right_only and not dircmp.diff_files
    elif source.is_file() and target.is_file():
        # Compare file content
        is_same = filecmp.cmp(source, target, shallow=False)

    if is_same:
        return True  # Same, skip

    # Conflict detected
    print()
    warn(f"Conflict detected: {target.name}")
    print(f"  Repo:   {source}")
    print(f"  Global: {target}")

    if force:
        if target.is_dir():
            shutil.rmtree(target)
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
        ok(f"Overwritten (force): {target.name}")
        return True

    if sys.stdin.isatty():
        # Interactive: show diff and ask
        if source.is_file() and target.is_file():
            print()
            try:
                subprocess.run(
                    ["diff", "--color=auto", str(source), str(target)],
                    capture_output=False,
                )
            except Exception:
                pass
        elif source.is_dir() and target.is_dir():
            print()
            try:
                subprocess.run(
                    ["diff", "-rq", str(source), str(target)],
                    capture_output=False,
                )
            except Exception:
                pass

        print()
        print("  [o] Overwrite  [k] Keep current  [s] Skip")
        choice = input("  Choice: ").strip().lower()

        if choice == "o":
            if target.is_dir():
                shutil.rmtree(target)
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
            ok(f"Overwritten: {target.name}")
            return True
        elif choice == "k":
            ok(f"Kept current: {target.name}")
            return False
        else:
            ok(f"Skipped: {target.name}")
            return False
    else:
        # Non-interactive: skip with warning
        warn(f"Skipping conflict (non-interactive): {target.name}")
        warn("Use --force to overwrite all")
        return False


def install_local_config(source: Path, target: Path, force: bool = False) -> bool:
    """Install config with merge support (for TOML files)."""
    # Remove old symlink
    if target.is_symlink():
        warn(f"{target.name} is symlinked - replacing with copy")
        target.unlink()
        shutil.copy2(source, target)
        return True

    if target.exists():
        if filecmp.cmp(source, target, shallow=False):
            return True  # Same, skip
        info(f"Merging {source.name} configurations into {target}...")
        run_node_script("merge-toml-config.js", str(source), str(target))
        return True

    shutil.copy2(source, target)
    return True


def count_files(directory: Path, pattern: str) -> int:
    """Count files matching pattern in directory."""
    if not directory.exists():
        return 0
    return len(list(directory.glob(pattern)))


def count_dirs(directory: Path) -> int:
    """Count subdirectories in directory."""
    if not directory.exists():
        return 0
    return len([d for d in directory.iterdir() if d.is_dir()])


def compile_agents(install_claude: bool, install_codex: bool, install_agy: bool) -> None:
    """Compile shared Markdown agents to CLI-specific formats."""
    info("Compiling custom agents...")
    flags = []
    if install_claude:
        flags.append("--claude")
    if install_codex:
        flags.append("--codex")
    if install_agy:
        flags.append("--agy")
    run_node_script("compile-agents.js", *flags)


def setup_claude(force: bool) -> None:
    """Setup Claude Code configuration."""
    info("Setting up Claude Code...")

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

    # Agents (written directly by compiler)
    ok(f"Agents ({count_files(CLAUDE_DIR / 'agents', '*.md')} files)")

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

    # Agents (written directly by compiler)
    ok(f"Agents ({count_files(CODEX_DIR / 'agents', '*.toml')} files)")

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
    # settings.json — merge by default, overwrite with --force
    if force:
        copy_config(REPO_DIR / "gemini" / "settings.json", agy_cli_dir / "settings.json", force)
    else:
        merge_json(REPO_DIR / "gemini" / "settings.json", agy_cli_dir / "settings.json")
    ok("settings.json")



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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Coding Config Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./install.py                    # Install all (Claude, Codex, agy)
  ./install.py --claude           # Only Claude
  ./install.py --codex --force    # Codex, overwrite all
  ./install.py --all --force      # All, overwrite all
        """,
    )
    parser.add_argument("--claude", action="store_true", help="Only install/configure Claude Code")
    parser.add_argument("--codex", action="store_true", help="Only install/configure Codex CLI")
    parser.add_argument("--agy", action="store_true", help="Only install/configure Antigravity CLI (agy)")
    parser.add_argument("--all", action="store_true", help="Install/configure all three (default)")
    parser.add_argument("--none", action="store_true", help="Do not install/configure any CLI targets (sync only)")
    parser.add_argument("--force", action="store_true", help="Overwrite all without asking")
    parser.add_argument("--project", type=str, help="Target project directory to configure project-level hooks (defaults to current repo)")

    args = parser.parse_args()

    # Default: install all if no specific flag and not --none
    if not (args.claude or args.codex or args.agy or args.none):
        args.all = True

    install_claude = (args.all or args.claude) and not args.none
    install_codex = (args.all or args.codex) and not args.none
    install_agy = (args.all or args.agy) and not args.none

    # Compile agents
    compile_agents(install_claude, install_codex, install_agy)

    # Setup each CLI
    if install_claude:
        setup_claude(args.force)

    if install_codex:
        setup_codex(args.force)

    if install_agy:
        setup_agy(args.force)

    # Update MCP configs
    update_mcp_configs(install_claude, install_agy)

    # Sync disabled MCP servers
    sync_mcp_disabled()

    # Target project directory for hooks
    target_project_dir = Path(args.project).resolve() if args.project else REPO_DIR

    # Install Graphify git hooks if graphify is available
    if shutil.which("graphify"):
        info(f"Initializing Graphify knowledge graph in {target_project_dir}...")
        try:
            subprocess.run(["graphify", "update", "."], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(target_project_dir))
            ok("Graphify graph initialized")
        except subprocess.CalledProcessError:
            warn("Failed to initialize Graphify graph")

        info(f"Installing Graphify git hooks in {target_project_dir}...")
        try:
            subprocess.run(["graphify", "hook", "install"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(target_project_dir))
            ok("Graphify git hooks")
        except subprocess.CalledProcessError:
            warn("Failed to install Graphify git hooks")

        # Scan available assistants
        avail_assistants = []
        if install_claude and shutil.which("claude"):
            avail_assistants.append("claude")
        if install_agy and shutil.which("agy"):
            avail_assistants.append("gemini")
        if install_codex and shutil.which("codex"):
            avail_assistants.append("codex")

        if not avail_assistants:
            warn("No AI assistants (claude, agy, codex) detected on $PATH. Skipping project-level hooks.")
            return

        to_configure = list(avail_assistants)  # default: configure all available

        # If interactive and not --force, ask the user
        if sys.stdin.isatty() and not args.force:
            print("\n" + "="*60)
            print("Select which AI assistants to configure for this project:")
            for i, assistant in enumerate(avail_assistants, 1):
                name = {
                    "claude": "Claude Code (claude)",
                    "gemini": "Gemini / Antigravity (agy)",
                    "codex": "Codex CLI (codex)"
                }.get(assistant, assistant)
                print(f"  [{i}] {name}")
            print("  [A] All of the above (default)")
            print("="*60)
            
            try:
                choice = input("Enter choices (e.g. '1,3' or 'A', default: A): ").strip()
                if choice and choice.upper() != "A":
                    chosen_indices = [c.strip() for c in choice.split(",")]
                    chosen_assistants = []
                    for idx in chosen_indices:
                        if idx.isdigit():
                            val = int(idx) - 1
                            if 0 <= val < len(avail_assistants):
                                chosen_assistants.append(avail_assistants[val])
                    if chosen_assistants:
                        to_configure = chosen_assistants
            except (KeyboardInterrupt, EOFError):
                print("\nUsing default (All).")

        info(f"Configuring Graphify project-level hooks for: {', '.join(to_configure)} in {target_project_dir}...")
        configure_project_assistants(target_project_dir, to_configure)


    print()
    print("Done! Restart Claude Code / Codex CLI / agy to pick up changes.")
    print()
    print("NOTE: Re-run ./install.py any time to refresh shared assets.")
    print("      Personal Codex trusted projects stay in ~/.codex/config.toml.")


if __name__ == "__main__":
    main()
