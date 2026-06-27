#!/usr/bin/env python3
"""Standalone installer for Antigravity CLI wrapper (agy)."""

import os
import shutil
import sys
from pathlib import Path

from installer.constants import REAL_HOME

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

    print("\n🎉 Standalone Antigravity CLI (agy) uninstallation completed successfully!")

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
        if dst_wrapper.exists() and not real_agy.exists():
            try:
                existing = dst_wrapper.read_text(encoding="utf-8", errors="ignore")
                managed_wrapper = src_wrapper.read_text(encoding="utf-8", errors="ignore")
                if existing != managed_wrapper:
                    shutil.copy2(dst_wrapper, real_agy)
                    try:
                        real_agy.chmod(0o755)
                    except Exception:
                        pass
                    print(f"   Preserved existing Antigravity binary as {real_agy}")
                else:
                    print(f"⚠️ Warning: {real_agy} is missing. Install the official Antigravity CLI before launching agy.")
            except Exception as e:
                print(f"⚠️ Warning: Failed to preserve existing agy binary: {e}")
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

    print("\n🎉 Standalone Antigravity CLI (agy) installation completed successfully!")
    print(f"\nMake sure your PATH environment variable includes: {bin_dir}")
    print("You can run it globally by typing: agy status")

if __name__ == "__main__":
    main()
