#!/usr/bin/env python3
"""
Update global Claude settings to use improved Graphify hook

This script updates ~/.claude/settings.json to use the improved hook script.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

def backup_global_settings() -> Path:
    """Create backup of global settings.json."""
    settings_path = Path.home() / ".claude" / "settings.json"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = settings_path.parent / f"settings.backup.{timestamp}.json"
    shutil.copy2(settings_path, backup_path)
    print(f"✅ Global backup created: {backup_path}")
    return backup_path

def update_global_settings(hook_script_path: str) -> bool:
    """Update global settings.json with improved hook."""
    settings_path = Path.home() / ".claude" / "settings.json"

    try:
        # Read current settings
        with open(settings_path, 'r') as f:
            settings = json.load(f)

        # Update hook commands
        if 'hooks' in settings and 'PreToolUse' in settings['hooks']:
            for hook_config in settings['hooks']['PreToolUse']:
                if 'hooks' in hook_config:
                    for hook in hook_config['hooks']:
                        if 'command' in hook:
                            # Replace old hook command with new one
                            if 'graphify' in hook['command'].lower():
                                hook['command'] = f"""# ai-coding-config:graphify-managed (improved)
python3 '{hook_script_path}'"""
                                print(f"✅ Updated global hook: {hook_config.get('matcher', 'unknown')}")

        # Write updated settings
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2)
            f.write('\n')

        print(f"✅ Global settings updated: {settings_path}")
        return True

    except Exception as e:
        print(f"❌ Error updating global settings: {e}")
        return False

def main():
    """Main function."""
    hook_script_path = Path("scripts/graphify-hook-improved.py").resolve()

    if not hook_script_path.exists():
        print(f"❌ Hook script not found: {hook_script_path}")
        return 1

    print("🔄 Updating global Graphify hook settings...\n")

    # Step 1: Backup
    backup_path = backup_global_settings()

    # Step 2: Update
    if not update_global_settings(str(hook_script_path)):
        print("❌ Update failed, restoring backup...")
        settings_path = Path.home() / ".claude" / "settings.json"
        shutil.copy2(backup_path, settings_path)
        return 1

    print("\n🎉 Global hook settings updated successfully!")
    print(f"\n📝 Next steps:")
    print(f"   1. Restart Claude Code to apply changes")
    print(f"   2. Test with: GRAPHIFY_DEBUG=1 claude -p 'test'")
    print(f"   3. Use GRAPHIFY_BYPASS=1 to temporarily disable hooks")

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
