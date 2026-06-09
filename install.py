#!/usr/bin/env python3
"""AI Coding Config Installer.

Copies shared Claude/Codex/Gemini assets from this repo to their expected locations.
Detects conflicts and lets user decide: overwrite, keep, or skip.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Exposed attributes for backwards compatibility / tests
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

from installer import (
    info,
    ok,
    warn,
    error,
    setup_claude,
    setup_codex,
    setup_agy,
    setup_cli_wrapper,
    uninstall_global,
    uninstall_project,
    update_mcp_configs,
    sync_mcp_disabled,
    compile_agents,
    configure_project_assistants,
)

REPO_DIR = Path(__file__).resolve().parent

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
    parser.add_argument("--uninstall", action="store_true", help="Uninstall all global and/or project-level configurations and hooks")

    args = parser.parse_args()

    if args.uninstall:
        if args.project:
            target_project_dir = Path(args.project).resolve()
            uninstall_project(target_project_dir)
        else:
            uninstall_global()
        return

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

    # Automatically install/update the global command wrapper
    setup_cli_wrapper(REPO_DIR)

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
