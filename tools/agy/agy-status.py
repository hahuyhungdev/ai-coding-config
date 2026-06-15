#!/usr/bin/env python3
import sys
from accounts import (
    get_account_status, list_accounts, show_weekly_usage, select_account,
    remove_account, import_current_token, add_token_from_input, import_from_file,
    clean_conversations, delete_conversation
)
from switch import auto_switch_account, post_check_and_switch, rotate_account

def print_guide():
    print("""
🤖 AGYSWAP (Antigravity CLI Account Manager) Guide
==================================================
agyswap is a custom utility wrapper to check, switch, and manage multiple 
accounts for the Antigravity (agy) CLI.

Commands:
  agyswap                       Rotate to the next account and launch agy CLI.
  agyswap <agy-args...>         Rotate to the next account and run agy with the arguments.
  
  agyswap status                Show all accounts, active status, and remaining quota.
                                (aliases: current, info, show)

  agyswap list                  List all accounts (quick, no quota check).
                                (aliases: ls, accounts)

  agyswap weekly                Show local 7-day usage estimate from CLI logs.
                                (aliases: week, usage-week, weekly-usage)
                                
  agyswap select <target>       Directly switch the active account by 1-based index or email name.
                                (aliases: choose, use)
                                Example:
                                  agyswap select 1
                                  agyswap select zerocadev
                                  
  agyswap add-current           Import the current active token into accounts.json pool.
                                (aliases: import, save)
                                Useful when you log in manually using the real agy command.

  agyswap add-token             Paste token JSON directly from clipboard.
                                (aliases: paste, new-token)
                                Example:
                                  agyswap add-token
                                  agyswap add-token myaccount

  agyswap import-file <path>    Import token from a JSON file into accounts.json.
                                (aliases: add-file, load)
                                Example:
                                  agyswap import-file ~/token.json
                                  agyswap import-file ~/token.json myaccount
                                
  agyswap clean                 Clean up all automated/orphaned test sessions.
                                (aliases: cleanup, prune)

  agyswap delete                List active conversations to select for deletion.
  agyswap delete <target>       Delete a conversation by index, ID, or search keyword.
                                (aliases: remove, rm)

  agyswap remove-account        List all accounts to select for removal.
  agyswap remove-account <tgt>  Remove an account by index or name/email.
                                (aliases: rm-account, delete-account)

  agyswap help                  Show this guide.
                                (aliases: guide, -h, --help)
""")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd in ["rotate", "next"]:
            rotate_account()
        elif cmd == "auto-switch":
            auto_switch_account()
        elif cmd == "post-check":
            post_check_and_switch()
        elif cmd in ["status", "current", "info", "show"]:
            get_account_status()
        elif cmd in ["list", "ls", "accounts"]:
            list_accounts()
        elif cmd in ["weekly", "week", "usage-week", "weekly-usage"]:
            show_weekly_usage()
        elif cmd in ["select", "choose", "use"]:
            if len(sys.argv) > 2:
                select_account(sys.argv[2])
            else:
                print("❌ Please specify an account index or email (e.g. 'agyswap select 1' or 'agyswap select zerocadev')")
        elif cmd in ["add-current", "import", "save"]:
            if len(sys.argv) > 2:
                import_current_token(sys.argv[2])
            else:
                import_current_token(None)
        elif cmd in ["add-token", "paste", "new-token"]:
            custom_email = sys.argv[2] if len(sys.argv) > 2 else None
            add_token_from_input(custom_email)
        elif cmd in ["import-file", "add-file", "load"]:
            if len(sys.argv) > 2:
                file_path = sys.argv[2]
                custom_email = sys.argv[3] if len(sys.argv) > 3 else None
                import_from_file(file_path, custom_email)
            else:
                print("❌ Usage: agyswap import-file <path.json> [email_label]")
                print("   Example: agyswap import-file ~/token.json myaccount")
        elif cmd in ["clean", "cleanup", "prune"]:
            clean_conversations()
        elif cmd in ["remove-account", "rm-account", "delete-account"]:
            if len(sys.argv) > 2:
                remove_account(sys.argv[2])
            else:
                remove_account(None)
        elif cmd in ["delete", "remove", "rm"]:
            if len(sys.argv) > 2:
                delete_conversation(sys.argv[2])
            else:
                delete_conversation(None)
        elif cmd in ["help", "guide", "-h", "--help"]:
            print_guide()
        else:
            print(f"❌ Unknown command: {cmd}")
            print("Available commands: status, list, select <index_or_email>, add-current, add-token, import-file <path>, clean, delete, help")
    else:
        get_account_status()
