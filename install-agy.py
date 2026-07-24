#!/usr/bin/env python3
"""Standalone installer for Antigravity CLI wrapper (agy)."""

import os
import shutil
import sys
import json
from pathlib import Path

from installer.constants import REAL_HOME

def _load_settings(settings_file):
    if not settings_file.exists():
        return {}
    try:
        with open(settings_file, "r") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _upsert_wildcard_hook(hooks_cfg, event, hook):
    event_list = hooks_cfg.get(event, [])
    if not isinstance(event_list, list):
        event_list = []

    wildcard_entry = None
    for entry in event_list:
        if isinstance(entry, dict) and entry.get("matcher") == "*":
            wildcard_entry = entry
            break

    if wildcard_entry is None:
        wildcard_entry = {"matcher": "*", "hooks": []}
        event_list.append(wildcard_entry)

    entry_hooks = wildcard_entry.get("hooks", [])
    if not isinstance(entry_hooks, list):
        entry_hooks = []
        wildcard_entry["hooks"] = entry_hooks

    for existing_hook in entry_hooks:
        if isinstance(existing_hook, dict) and existing_hook.get("name") == hook["name"]:
            existing_hook.update(hook)
            break
    else:
        entry_hooks.append(dict(hook))

    hooks_cfg[event] = event_list


def configure_quota_hooks(home=REAL_HOME, agy_cli_dir=None):
    home = Path(home)
    agy_cli_dir = Path(agy_cli_dir) if agy_cli_dir is not None else home / ".gemini" / "antigravity-cli"
    settings_files = [
        home / ".gemini" / "settings.json",
        agy_cli_dir / "settings.json",
    ]

    # Find the python command to use
    python_cmd = "python" if sys.platform == "win32" or not shutil.which("python3") else "python3"

    before_hook = {
        "name": "quota-pre-check",
        "type": "command",
        "command": f"{python_cmd} {agy_cli_dir}/before_agent.py",
        "timeout": 10000,
        "description": "Pre-check active account quota",
    }
    after_hook = {
        "name": "quota-auto-switch",
        "type": "command",
        "command": f"{python_cmd} {agy_cli_dir}/after_agent.py",
        "timeout": 10000,
        "description": "Switch account on quota error and retry",
    }

    for settings_file in settings_files:
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings = _load_settings(settings_file)
        hooks_cfg = settings.get("hooks")
        if not isinstance(hooks_cfg, dict):
            hooks_cfg = {}
            settings["hooks"] = hooks_cfg

        _upsert_wildcard_hook(hooks_cfg, "UserPromptSubmit", before_hook)
        _upsert_wildcard_hook(hooks_cfg, "Stop", after_hook)

        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=2)


def uninstall():
    print("🗑️ Uninstalling Antigravity CLI (agy) standalone...")

    # Define paths
    home = REAL_HOME
    gemini_dir = home / ".gemini" / "config"
    agy_cli_dir = home / ".gemini" / "antigravity-cli"
    bin_dir = home / ".local" / "bin"
    repo_dir = Path(__file__).resolve().parent

    # 1. Remove wrappers
    for name in ["agy", "agy.bat"]:
        p = bin_dir / name
        if p.exists():
            try:
                p.unlink()
                print(f"   Removed global wrapper {p}")
            except Exception as e:
                print(f"⚠️ Warning: Failed to remove global wrapper {p}: {e}")

    # 2. Remove ANTIGRAVITY.md
    antigravity_md = gemini_dir / "ANTIGRAVITY.md"
    if antigravity_md.exists():
        try:
            antigravity_md.unlink()
            print(f"   Removed {antigravity_md}")
        except Exception as e:
            print(f"⚠️ Warning: Failed to remove {antigravity_md}: {e}")

    # 3. Clean up copied skills
    src_skills = repo_dir / "skills"
    if src_skills.exists():
        for item in src_skills.iterdir():
            if item.is_dir():
                dst_item = gemini_dir / "skills" / item.name
                if dst_item.exists():
                    try:
                        shutil.rmtree(dst_item)
                        print(f"   Removed skill {item.name}")
                    except Exception as e:
                        print(f"⚠️ Warning: Failed to remove skill {item.name}: {e}")

    # 4. Clean up copied agents
    src_agents = repo_dir / "agents"
    if src_agents.exists():
        for item in src_agents.glob("*.md"):
            dst_item = gemini_dir / "agents" / item.name
            if dst_item.exists():
                try:
                    dst_item.unlink()
                    print(f"   Removed agent {item.name}")
                except Exception as e:
                    print(f"⚠️ Warning: Failed to remove agent {item.name}: {e}")

    # 4b. Clean up copied custom commands
    dest_dirs = [
        gemini_dir / "commands",
        home / ".gemini" / "commands",
        home / ".claude" / "commands",
        repo_dir / ".gemini" / "commands",
        repo_dir / ".claude" / "commands"
    ]
    for d in dest_dirs:
        if d.exists():
            for name in ["rotate.toml", "rotate.md"]:
                p = d / name
                if p.exists():
                    try:
                        p.unlink()
                        print(f"   Removed custom command {name} from {d}")
                    except Exception as e:
                        print(f"⚠️ Warning: Failed to remove custom command {name} from {d}: {e}")

    # 5. Remove only installed modules; preserve credentials and runtime data.
    src_dir = repo_dir / "tools" / "agy"
    if agy_cli_dir.exists() and src_dir.exists():
        for item in src_dir.glob("*.py"):
            installed_item = agy_cli_dir / item.name
            try:
                installed_item.unlink(missing_ok=True)
            except Exception as e:
                print(f"⚠️ Warning: Failed to remove {installed_item}: {e}")
        try:
            (agy_cli_dir / "README.md").unlink(missing_ok=True)
        except Exception as e:
            print(f"⚠️ Warning: Failed to remove {agy_cli_dir / 'README.md'}: {e}")
        print(f"   Removed installed modules from {agy_cli_dir}")

    # 6. Remove BeforeAgent and AfterAgent hooks from ~/.gemini/settings.json
    official_settings_file = home / ".gemini" / "settings.json"
    if official_settings_file.exists():
        try:
            import json
            with open(official_settings_file, "r") as f:
                official_settings = json.load(f)

            updated = False
            if "hooks" in official_settings and isinstance(official_settings["hooks"], dict):
                hooks_cfg = official_settings["hooks"]

                # Clean UserPromptSubmit
                if "UserPromptSubmit" in hooks_cfg:
                    before_list = hooks_cfg["UserPromptSubmit"]
                    new_before = []
                    for entry in before_list:
                        if isinstance(entry, dict) and "hooks" in entry:
                            entry["hooks"] = [h for h in entry["hooks"] if isinstance(h, dict) and h.get("name") != "quota-pre-check"]
                            if entry["hooks"]:
                                new_before.append(entry)
                        else:
                            new_before.append(entry)
                    hooks_cfg["UserPromptSubmit"] = new_before
                    updated = True

                # Clean Stop
                if "Stop" in hooks_cfg:
                    after_list = hooks_cfg["Stop"]
                    new_after = []
                    for entry in after_list:
                        if isinstance(entry, dict) and "hooks" in entry:
                            entry["hooks"] = [h for h in entry["hooks"] if isinstance(h, dict) and h.get("name") != "quota-auto-switch"]
                            if entry["hooks"]:
                                new_after.append(entry)
                        else:
                            new_after.append(entry)
                    hooks_cfg["Stop"] = new_after
                    updated = True

                # Clean PreToolUse
                if "PreToolUse" in hooks_cfg:
                    pt_list = hooks_cfg["PreToolUse"]
                    new_pt = []
                    for entry in pt_list:
                        if isinstance(entry, dict) and "hooks" in entry:
                            entry["hooks"] = [h for h in entry["hooks"] if isinstance(h, dict) and h.get("name") not in ["quota-pre-check-tool", "quota-pre-check"]]
                            if entry["hooks"]:
                                new_pt.append(entry)
                        else:
                            new_pt.append(entry)
                    hooks_cfg["PreToolUse"] = new_pt
                    updated = True

                # Clean BeforeAgent
                if "BeforeAgent" in hooks_cfg:
                    ba_list = hooks_cfg["BeforeAgent"]
                    new_ba = []
                    for entry in ba_list:
                        if isinstance(entry, dict) and "hooks" in entry:
                            entry["hooks"] = [h for h in entry["hooks"] if isinstance(h, dict) and h.get("name") != "quota-pre-check"]
                            if entry["hooks"]:
                                new_ba.append(entry)
                        else:
                            new_ba.append(entry)
                    hooks_cfg["BeforeAgent"] = new_ba
                    updated = True

                # Clean AfterAgent
                if "AfterAgent" in hooks_cfg:
                    aa_list = hooks_cfg["AfterAgent"]
                    new_aa = []
                    for entry in aa_list:
                        if isinstance(entry, dict) and "hooks" in entry:
                            entry["hooks"] = [h for h in entry["hooks"] if isinstance(h, dict) and h.get("name") != "quota-auto-switch"]
                            if entry["hooks"]:
                                new_aa.append(entry)
                        else:
                            new_aa.append(entry)
                    hooks_cfg["AfterAgent"] = new_aa
                    updated = True

            if updated:
                with open(official_settings_file, "w") as f:
                    json.dump(official_settings, f, indent=2)
                print(f"   Removed hooks from {official_settings_file}")
        except Exception as e:
            print(f"⚠️ Warning: Failed to clean hooks from {official_settings_file}: {e}")

    print("\n🎉 Standalone Antigravity CLI (agy) uninstallation completed successfully!")

def get_windows_home():
    """Helper to locate Windows home directory when running inside WSL."""
    import os
    if os.environ.get("WSL_DISTRO_NAME"):
        users_dir = Path("/mnt/c/Users")
        if users_dir.exists():
            candidates = []
            for item in users_dir.iterdir():
                if item.is_dir() and item.name not in ("All Users", "Default", "Default User", "Public"):
                    if (item / ".gemini").exists():
                        return item
                    candidates.append(item)
            if candidates:
                return candidates[0]
    return None


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Standalone installer and uninstaller for Antigravity CLI (agy).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--uninstall", "-u", action="store_true", help="Uninstall agy wrapper, status scripts, and assets"
    )
    args = parser.parse_args()

    if args.uninstall:
        uninstall()
        return

    print("🚀 Installing Antigravity CLI (agy) standalone...")

    # Define paths
    repo_dir = Path(__file__).resolve().parent
    home = REAL_HOME
    gemini_dir = home / ".gemini" / "config"
    agy_cli_dir = home / ".gemini" / "antigravity-cli"
    bin_dir = home / ".local" / "bin"

    # Create directories
    gemini_dir.mkdir(parents=True, exist_ok=True)
    (gemini_dir / "skills").mkdir(parents=True, exist_ok=True)
    (gemini_dir / "agents").mkdir(parents=True, exist_ok=True)
    agy_cli_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy modular Python files
    src_dir = repo_dir / "tools" / "agy"
    if src_dir.exists():
        for item in src_dir.glob("*.py"):
            shutil.copy2(item, agy_cli_dir / item.name)
        readme = src_dir / "README.md"
        if readme.exists():
            shutil.copy2(readme, agy_cli_dir / readme.name)
        print(f"   Installed modular Python files to {agy_cli_dir}")
    else:
        print(f"❌ Error: {src_dir} not found.", file=sys.stderr)
        sys.exit(1)

    # 2. Copy bash wrapper (for Ubuntu/Linux, WSL, Git Bash)
    src_wrapper = src_dir / "agy"
    if src_wrapper.exists():
        dst_wrapper = bin_dir / "agy"
        real_agy = bin_dir / "agy-bin"
        if not real_agy.exists():
            if dst_wrapper.exists():
                try:
                    existing = dst_wrapper.read_text(encoding="utf-8", errors="ignore")
                    if "REAL_AGY_OVERRIDE" not in existing:
                        shutil.copy2(dst_wrapper, real_agy)
                        try:
                            real_agy.chmod(0o755)
                        except Exception:
                            pass
                        print(f"   Preserved existing Antigravity binary as {real_agy}")
                except Exception as e:
                    print(f"⚠️ Warning: Failed to preserve existing agy binary: {e}")
            
            if not real_agy.exists():
                found_path = None
                path_dirs = os.environ.get("PATH", "").split(os.pathsep)
                for d in path_dirs:
                    if not d:
                        continue
                    try:
                        d_path = Path(d).resolve()
                    except Exception:
                        continue
                    if d_path == bin_dir.resolve():
                        continue
                    for name in ["agy", "agy.exe", "agy.cmd", "agy.bat"]:
                        candidate = d_path / name
                        if candidate.exists() and not candidate.is_dir():
                            try:
                                content = candidate.read_text(encoding="utf-8", errors="ignore")
                                if "REAL_AGY_OVERRIDE" not in content:
                                    found_path = candidate
                                    break
                            except Exception:
                                found_path = candidate
                                break
                    if found_path:
                        break
                
                if found_path:
                    try:
                        shutil.copy2(found_path, real_agy)
                        try:
                            real_agy.chmod(0o755)
                        except Exception:
                            pass
                        print(f"   Preserved existing Antigravity binary found at {found_path} as {real_agy}")
                    except Exception as e:
                        print(f"⚠️ Warning: Failed to copy {found_path} to {real_agy}: {e}")
                else:
                    print(f"⚠️ Warning: {real_agy} is missing. Install the official Antigravity CLI before launching agy.")
        shutil.copy2(src_wrapper, dst_wrapper)
        try:
            dst_wrapper.chmod(0o755)
        except Exception:
            pass
        print(f"   Installed agy bash wrapper to {dst_wrapper}")
    else:
        print(f"❌ Error: {src_wrapper} not found.", file=sys.stderr)
        sys.exit(1)

    # 3. Create/copy Windows CMD wrapper (agy.bat)
    dst_bat = bin_dir / "agy.bat"
    bat_content = '@echo off\npython "%USERPROFILE%\\.gemini\\antigravity-cli\\agy-status.py" %*\n'
    try:
        dst_bat.write_text(bat_content, encoding="utf-8")
        print(f"   Created and installed agy.bat wrapper to {dst_bat}")
    except Exception as e:
        print(f"⚠️ Warning: Failed to write Windows agy.bat wrapper: {e}")


    # 4. Copy ANTIGRAVITY.md
    src_readme = repo_dir / "gemini" / "ANTIGRAVITY.md"
    if src_readme.exists():
        shutil.copy2(src_readme, gemini_dir / "ANTIGRAVITY.md")
        print(f"   Copied ANTIGRAVITY.md to {gemini_dir / 'ANTIGRAVITY.md'}")

    # 5. Copy settings.json (copying if not exists)
    src_settings = repo_dir / "gemini" / "settings.json"
    dst_settings = agy_cli_dir / "settings.json"
    if src_settings.exists():
        if not dst_settings.exists():
            shutil.copy2(src_settings, dst_settings)
            print(f"   Created default settings.json in {dst_settings}")
        else:
            print(f"   settings.json already exists at {dst_settings}, keeping existing configuration.")

    # 6. Copy skills if directory exists
    src_skills = repo_dir / "skills"
    if src_skills.exists():
        dst_skills = gemini_dir / "skills"
        if dst_skills.exists():
            for item in dst_skills.iterdir():
                if item.is_dir() and not (src_skills / item.name).exists():
                    shutil.rmtree(item)
        for item in src_skills.iterdir():
            if item.is_dir():
                dst_item = gemini_dir / "skills" / item.name
                if dst_item.exists():
                    shutil.rmtree(dst_item)
                shutil.copytree(item, dst_item)
        print(f"   Copied skills to {gemini_dir / 'skills'}")

    # 7. Compile and copy custom agents
    src_agents = repo_dir / "agents"
    dst_agents = gemini_dir / "agents"
    if src_agents.exists():
        if dst_agents.exists():
            shutil.rmtree(dst_agents)
        dst_agents.mkdir(parents=True, exist_ok=True)

        for item in src_agents.glob("*.md"):
            try:
                content = item.read_text(encoding="utf-8")
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter_lines = parts[1].strip().splitlines()
                    clean_lines = []
                    in_codex = False
                    for line in frontmatter_lines:
                        stripped = line.strip()
                        if not stripped:
                            continue
                        if stripped.startswith("codex:"):
                            in_codex = True
                            continue
                        if in_codex:
                            if line.startswith(" ") or line.startswith("\t"):
                                continue
                            else:
                                in_codex = False
                        clean_lines.append(line)

                    clean_frontmatter = "\n".join(clean_lines)
                    clean_content = f"---\n{clean_frontmatter}\n---\n{parts[2]}"
                    (dst_agents / item.name).write_text(clean_content, encoding="utf-8")
                else:
                    shutil.copy2(item, dst_agents / item.name)
            except Exception as e:
                print(f"⚠️ Warning: Failed to compile agent {item.name}: {e}")
                try:
                    shutil.copy2(item, dst_agents / item.name)
                except Exception:
                    pass
        print(f"   Compiled and copied agents to {dst_agents}")

    # 8. Configure BeforeAgent and AfterAgent hooks in official ~/.gemini/settings.json
    official_settings_file = home / ".gemini" / "settings.json"
    official_settings = {}
    if official_settings_file.exists():
        try:
            with open(official_settings_file, "r") as f:
                official_settings = json.load(f)
        except Exception as e:
            print(f"⚠️ Warning: Failed to parse {official_settings_file}: {e}")

    # Ensure hooks dictionary exists
    if "hooks" not in official_settings or not isinstance(official_settings["hooks"], dict):
        official_settings["hooks"] = {}

    hooks_cfg = official_settings["hooks"]

    # Find the python command to use
    python_cmd = "python" if sys.platform == "win32" or not shutil.which("python3") else "python3"

    # UserPromptSubmit hook
    before_hook = {
        "name": "quota-pre-check",
        "type": "command",
        "command": f"{python_cmd} {agy_cli_dir}/before_agent.py",
        "timeout": 10000,
        "description": "Pre-check active account quota"
    }

    # We want UserPromptSubmit entry for matcher "*"
    before_list = hooks_cfg.get("UserPromptSubmit", [])
    if not isinstance(before_list, list):
        before_list = []

    wildcard_before = None
    for entry in before_list:
        if isinstance(entry, dict) and entry.get("matcher") == "*":
            wildcard_before = entry
            break

    if wildcard_before is None:
        wildcard_before = {"matcher": "*", "hooks": []}
        before_list.append(wildcard_before)

    hook_exists = False
    for h in wildcard_before["hooks"]:
        if isinstance(h, dict) and h.get("name") == "quota-pre-check":
            h["command"] = before_hook["command"]  # Update path
            hook_exists = True
            break
    if not hook_exists:
        wildcard_before["hooks"].append(before_hook)

    hooks_cfg["UserPromptSubmit"] = before_list

    # Stop hook
    after_hook = {
        "name": "quota-auto-switch",
        "type": "command",
        "command": f"{python_cmd} {agy_cli_dir}/after_agent.py",
        "timeout": 10000,
        "description": "Switch account on quota error and retry"
    }

    after_list = hooks_cfg.get("Stop", [])
    if not isinstance(after_list, list):
        after_list = []

    wildcard_after = None
    for entry in after_list:
        if isinstance(entry, dict) and entry.get("matcher") == "*":
            wildcard_after = entry
            break

    if wildcard_after is None:
        wildcard_after = {"matcher": "*", "hooks": []}
        after_list.append(wildcard_after)

    hook_exists = False
    for h in wildcard_after["hooks"]:
        if isinstance(h, dict) and h.get("name") == "quota-auto-switch":
            h["command"] = after_hook["command"]  # Update path
            hook_exists = True
            break
    if not hook_exists:
        wildcard_after["hooks"].append(after_hook)

    hooks_cfg["Stop"] = after_list

    # PreToolUse hook
    tool_hook = {
        "name": "quota-pre-check-tool",
        "type": "command",
        "command": f"{python_cmd} {agy_cli_dir}/before_agent.py",
        "timeout": 10000,
        "description": "Pre-check active account quota before tool use"
    }

    tool_list = hooks_cfg.get("PreToolUse", [])
    if not isinstance(tool_list, list):
        tool_list = []

    # Ensure Gemini specific matchers exist
    existing_matchers = [entry.get("matcher") for entry in tool_list if isinstance(entry, dict)]
    for gm in ["Bash", "Read", "Write", "Grep"]:
        if gm not in existing_matchers:
            tool_list.insert(0, {"matcher": gm, "hooks": []})

    # Prepend to all existing specific matchers
    for entry in tool_list:
        if isinstance(entry, dict) and "hooks" in entry and entry.get("matcher") != "*":
            exists = False
            for h in entry["hooks"]:
                if isinstance(h, dict) and h.get("name") == "quota-pre-check-tool":
                    h["command"] = tool_hook["command"]
                    exists = True
                    break
            if not exists:
                entry["hooks"].insert(0, tool_hook)

    # Also add wildcard * entry as a fallback at the end
    wildcard_tool = None
    for entry in tool_list:
        if isinstance(entry, dict) and entry.get("matcher") == "*":
            wildcard_tool = entry
            break

    if wildcard_tool is None:
        wildcard_tool = {"matcher": "*", "hooks": []}
        tool_list.append(wildcard_tool)

    hook_exists = False
    for h in wildcard_tool["hooks"]:
        if isinstance(h, dict) and h.get("name") == "quota-pre-check-tool":
            h["command"] = tool_hook["command"]
            hook_exists = True
            break
    if not hook_exists:
        wildcard_tool["hooks"].append(tool_hook)

    hooks_cfg["PreToolUse"] = tool_list

    try:
        with open(official_settings_file, "w") as f:
            json.dump(official_settings, f, indent=2)
        print(f"   Configured UserPromptSubmit & Stop hooks in {official_settings_file}")
    except Exception as e:
        print(f"⚠️ Warning: Failed to write to {official_settings_file}: {e}")

    try:
        configure_quota_hooks(home, agy_cli_dir)
        print(f"   Synced quota hooks to {official_settings_file} and {agy_cli_dir / 'settings.json'}")
    except Exception as e:
        print(f"⚠️ Warning: Failed to sync quota hooks: {e}")

    # 9. Copy custom commands to ~/.gemini/commands/, ~/.claude/commands/, and project-level commands
    src_commands = repo_dir / "tools" / "agy" / "commands"
    if src_commands.exists():
        dest_dirs = [
            gemini_dir / "commands",
            home / ".gemini" / "commands",
            home / ".claude" / "commands",
            repo_dir / ".gemini" / "commands",
            repo_dir / ".claude" / "commands"
        ]
        for d in dest_dirs:
            d.mkdir(parents=True, exist_ok=True)
            for item in src_commands.glob("*.*"):
                shutil.copy2(item, d / item.name)
            print(f"   Copied custom commands to {d}")

    print("\n🎉 Standalone Antigravity CLI (agy) installation completed successfully!")
    print(f"\nMake sure your PATH environment variable includes: {bin_dir}")
    print("You can run it globally by typing: agy status")

if __name__ == "__main__":
    main()
