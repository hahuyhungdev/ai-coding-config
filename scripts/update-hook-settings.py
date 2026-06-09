#!/usr/bin/env python3
"""
Update Claude settings.json to use improved Graphify hook

This script:
1. Backs up current settings.json
2. Updates hook commands to use improved hook script
3. Validates the new configuration
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

def backup_settings(settings_path: Path) -> Path:
    """Create backup of current settings.json."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = settings_path.parent / f"settings.backup.{timestamp}.json"
    shutil.copy2(settings_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    return backup_path

def update_hook_command(old_command: str, hook_script_path: str) -> str:
    """Update hook command to use improved script."""
    # The new command will call the improved hook script
    new_command = f"""# ai-coding-config:graphify-managed (improved)
python3 '{hook_script_path}'"""
    return new_command

def update_settings(settings_path: Path, hook_script_path: str) -> bool:
    """Update settings.json with improved hook."""
    try:
        # Read current settings
        with open(settings_path, 'r') as f:
            settings = json.load(f)

        # Update each hook command
        if 'hooks' in settings and 'PreToolUse' in settings['hooks']:
            for hook_config in settings['hooks']['PreToolUse']:
                if 'hooks' in hook_config:
                    for hook in hook_config['hooks']:
                        if 'command' in hook and 'graphify-managed' in hook['command']:
                            hook['command'] = update_hook_command(hook['command'], hook_script_path)
                            print(f"✅ Updated hook: {hook_config.get('matcher', 'unknown')}")

        # Write updated settings
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2)
            f.write('\n')

        print(f"✅ Settings updated: {settings_path}")
        return True

    except Exception as e:
        print(f"❌ Error updating settings: {e}")
        return False

def validate_settings(settings_path: Path) -> bool:
    """Validate the updated settings.json."""
    try:
        with open(settings_path, 'r') as f:
            settings = json.load(f)

        # Check structure
        if 'hooks' not in settings:
            print("❌ Missing 'hooks' key")
            return False

        if 'PreToolUse' not in settings['hooks']:
            print("❌ Missing 'PreToolUse' key")
            return False

        # Check that all hooks have commands
        for hook_config in settings['hooks']['PreToolUse']:
            if 'hooks' not in hook_config:
                print(f"❌ Missing 'hooks' in {hook_config.get('matcher', 'unknown')}")
                return False

            for hook in hook_config['hooks']:
                if 'command' not in hook:
                    print(f"❌ Missing 'command' in hook")
                    return False

        print("✅ Settings validation passed")
        return True

    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False

def main():
    """Main function."""
    settings_path = Path(".claude/settings.json")
    hook_script_path = Path("scripts/graphify-hook-improved.py").resolve()

    if not settings_path.exists():
        print(f"❌ Settings file not found: {settings_path}")
        return 1

    if not hook_script_path.exists():
        print(f"❌ Hook script not found: {hook_script_path}")
        return 1

    print("🔄 Updating Graphify hook settings...\n")

    # Step 1: Backup
    backup_path = backup_settings(settings_path)

    # Step 2: Update
    if not update_settings(settings_path, str(hook_script_path)):
        print("❌ Update failed, restoring backup...")
        shutil.copy2(backup_path, settings_path)
        return 1

    # Step 3: Validate
    if not validate_settings(settings_path):
        print("❌ Validation failed, restoring backup...")
        shutil.copy2(backup_path, settings_path)
        return 1

    print("\n🎉 Hook settings updated successfully!")
    print(f"\n📝 Next steps:")
    print(f"   1. Restart Claude Code to apply changes")
    print(f"   2. Test with: GRAPHIFY_DEBUG=1 claude -p 'test'")
    print(f"   3. Use GRAPHIFY_BYPASS=1 to temporarily disable hooks")

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
