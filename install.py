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
    configure_copilot_project,
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
    setup_cli_wrapper,
    uninstall_global,
    uninstall_project,
    update_mcp_configs,
    sync_mcp_disabled,
    compile_agents,
    configure_project_assistants,
    show_status,
)

REPO_DIR = Path(__file__).resolve().parent

def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Coding Config Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./install.py                    # Install all (Claude, Codex)
  ./install.py --claude           # Only Claude
  ./install.py --codex --force    # Codex, overwrite all
  ./install.py --all --force      # All, overwrite all
        """,
    )
    parser.add_argument("--claude", action="store_true", help="Only install/configure Claude Code")
    parser.add_argument("--codex", action="store_true", help="Only install/configure Codex CLI")
    parser.add_argument("--copilot", action="store_true", help="Only install/configure GitHub Copilot (VS Code)")
    parser.add_argument("--all", action="store_true", help="Install/configure all assistants (default)")
    parser.add_argument("--none", action="store_true", help="Do not install/configure any CLI targets (sync only)")
    parser.add_argument("--force", action="store_true", help="Overwrite all without asking")
    parser.add_argument("--project", type=str, help="Target project directory to configure project-level hooks (defaults to current repo)")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall all global and/or project-level configurations and hooks")
    parser.add_argument("--status", action="store_true", help="Show configuration status, active account, and token usage")
    parser.add_argument("--init-ai", action="store_true", help="Initialize Graphify graph with AI semantic extraction")
    parser.add_argument("--backend", type=str, default="gemini", help="LLM backend for AI extraction (default: gemini)")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.init_ai:
        import json
        # Determine target directory
        target_project_dir = Path(args.project).resolve() if args.project else Path.cwd()
        
        # Initialize key/model variables
        gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        claude_key = os.environ.get("ANTHROPIC_API_KEY")
        claude_base_url = os.environ.get("ANTHROPIC_BASE_URL")
        claude_model = os.environ.get("ANTHROPIC_MODEL")
        gemini_model = None
        
        # Load from ~/.gemini/antigravity-cli/settings.json
        if not gemini_key or not gemini_model:
            try:
                f_agy = Path.home() / ".gemini" / "antigravity-cli" / "settings.json"
                if f_agy.exists():
                    with open(f_agy, "r") as f:
                        data = json.load(f)
                        env_data = data.get("env", {})
                        if not gemini_key:
                            gemini_key = env_data.get("GEMINI_API_KEY") or env_data.get("GOOGLE_API_KEY")
                        if not gemini_model and "model" in data:
                            gemini_model = data["model"]
            except Exception:
                pass
                
        # Load from ~/.claude/settings.json
        if not claude_key or not claude_model:
            try:
                f_claude = Path.home() / ".claude" / "settings.json"
                if f_claude.exists():
                    with open(f_claude, "r") as f:
                        data = json.load(f)
                        env_data = data.get("env", {})
                        if not claude_key:
                            claude_key = env_data.get("ANTHROPIC_API_KEY")
                        if not claude_base_url and "ANTHROPIC_BASE_URL" in env_data:
                            claude_base_url = env_data["ANTHROPIC_BASE_URL"]
                        if not claude_model:
                            claude_model = env_data.get("ANTHROPIC_MODEL") or data.get("model")
            except Exception:
                pass
                
        # Auto-detect backend based on available keys
        has_explicit_backend = "--backend" in sys.argv
        backend = args.backend.lower()
        
        if not has_explicit_backend:
            if claude_key and not gemini_key:
                backend = "claude"
            elif gemini_key:
                backend = "gemini"
                
        # Validate and configure keys based on selected backend
        api_key = None
        selected_model = None
        if backend == "claude":
            api_key = claude_key
            selected_model = claude_model
            key_var = "ANTHROPIC_API_KEY"
            alt_key_var = None
        else:
            api_key = gemini_key
            selected_model = gemini_model
            key_var = "GEMINI_API_KEY"
            alt_key_var = "GOOGLE_API_KEY"
            
        # Try prompting the user if we are in an interactive terminal
        if not api_key and sys.stdin.isatty():
            print(f"\n[WARN] API key for {backend.upper()} is not set in your environment or configs.")
            try:
                val = input(f"Enter your API key for {backend.upper()} (will not be stored on disk): ").strip()
                if val:
                    api_key = val
            except (KeyboardInterrupt, EOFError):
                pass
                
        if not api_key:
            print(f"\n[ERROR] API key for {backend.upper()} is required. Set {key_var} and try again.")
            sys.exit(1)
            
        # Set the environment variables for the subprocess
        env = os.environ.copy()
        if backend == "claude":
            env["ANTHROPIC_API_KEY"] = api_key
            if claude_base_url:
                env["ANTHROPIC_BASE_URL"] = claude_base_url
            if claude_model:
                env["ANTHROPIC_MODEL"] = claude_model
        else:
            env["GEMINI_API_KEY"] = api_key
            env["GOOGLE_API_KEY"] = api_key
            if gemini_model:
                env["GEMINI_MODEL"] = gemini_model
            
        # Run graphify extract
        print(f"\n🚀 Running Graphify AI Semantic Extraction using {backend.upper()} in {target_project_dir}...")
        cmd = ["graphify", "extract", ".", "--mode", "deep", "--backend", backend]
        if selected_model:
            cmd.extend(["--model", selected_model])
            
        try:
            subprocess.run(cmd, cwd=str(target_project_dir), env=env, check=True)
            print("\n[OK] Graphify AI semantic graph initialized successfully!")
        except subprocess.CalledProcessError as e:
            print(f"\n[ERROR] Graphify AI extraction failed with exit code {e.returncode}")
            sys.exit(e.returncode)
        return

    if args.uninstall:
        if args.project:
            target_project_dir = Path(args.project).resolve()
            uninstall_project(target_project_dir)
        else:
            uninstall_global()
        return

    # Default: install all if no specific flag and not --none
    if not (args.claude or args.codex or args.copilot or args.none):
        args.all = True

    install_claude = (args.all or args.claude) and not args.none
    install_codex = (args.all or args.codex) and not args.none
    install_copilot = (args.all or args.copilot) and not args.none

    # Compile agents
    compile_agents(install_claude, install_codex)

    # Setup each CLI
    if install_claude:
        setup_claude(args.force)

    if install_codex:
        setup_codex(args.force)

    # Automatically install/update the global command wrapper
    setup_cli_wrapper(REPO_DIR)

    # Update MCP configs
    update_mcp_configs(install_claude)

    # Sync disabled MCP servers
    sync_mcp_disabled()

    # Target project directory for hooks
    target_project_dir = Path(args.project).resolve() if args.project else REPO_DIR

    # Install Graphify git hooks if graphify is available
    if not shutil.which("graphify"):
        # If running in a non-interactive environment (like force mode or CI), skip asking
        if args.force:
            info("Graphify is not installed. Force mode enabled, attempting auto-installation...")
            should_install = True
        else:
            print("\n[WARN] Graphify is not installed on your system.")
            print("Graphify is highly recommended to save up to 99.8% of your API tokens by querying subgraphs.")
            try:
                choice = input("Would you like to install it now via pip? (y/N): ").strip().lower()
                should_install = choice == 'y'
            except (KeyboardInterrupt, EOFError):
                should_install = False

        if should_install:
            info("Installing graphifyy package via pip...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "graphifyy"], check=True)
                ok("Graphify installed successfully!")
            except Exception as e:
                warn(f"Failed to install Graphify: {e}. Skipping Graphify setup.")

    if shutil.which("graphify"):
        # Install/upgrade the optimized Graphify CLI wrapper to ~/.local/bin/graphify
        try:
            graphify_bin = Path(shutil.which("graphify")).resolve()
            original_content = graphify_bin.read_text(encoding="utf-8")
            shebang = "#!/usr/bin/env python3"
            if original_content.startswith("#!"):
                shebang = original_content.splitlines()[0]
            
            wrapper_src = REPO_DIR / "scripts" / "graphify-wrapper.py"
            if wrapper_src.exists():
                wrapper_code = shebang + "\n" + wrapper_src.read_text(encoding="utf-8")
                graphify_bin.write_text(wrapper_code, encoding="utf-8")
                graphify_bin.chmod(0o755)
                ok("Graphify CLI wrapper optimized with call chains & recommendations")
        except Exception as wrapper_exc:
            warn(f"Failed to optimize Graphify CLI wrapper: {wrapper_exc}")

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
        if install_codex and shutil.which("codex"):
            avail_assistants.append("codex")
        if install_copilot:
            avail_assistants.append("copilot")

        if not avail_assistants:
            warn("No AI assistants (claude, codex, copilot) detected. Skipping project-level hooks.")
            return

        to_configure = list(avail_assistants)  # default: configure all available

        # If interactive and not --force, ask the user
        if sys.stdin.isatty() and not args.force:
            print("\n" + "="*60)
            print("Select which AI assistants to configure for this project:")
            for i, assistant in enumerate(avail_assistants, 1):
                name = {
                    "claude": "Claude Code (claude)",
                    "codex": "Codex CLI (codex)",
                    "copilot": "GitHub Copilot (VS Code)"
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
    print("Done! Restart Claude Code / Codex CLI to pick up changes.")
    print()
    print("NOTE: Re-run ./install.py any time to refresh shared assets.")
    print("      Personal Codex trusted projects stay in ~/.codex/config.toml.")


if __name__ == "__main__":
    main()
