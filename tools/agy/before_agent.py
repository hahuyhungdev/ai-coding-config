#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add tools/agy/ directory to python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import AGY_DIR, TOKEN_FILE
from switch import (
    is_account_blocked_or_low,
    select_replacement_index,
    _write_active_account,
    generate_quota_rollover,
    kill_ancestor_agy_bin,
)
from storage import load_accounts, active_account_index, write_accounts

def log(message):
    print(f"[BeforeAgent] {message}", file=sys.stderr)

def main():
    # Debug logging
    try:
        debug_log = os.path.join(AGY_DIR, "brain/hook_debug.log")
        with open(debug_log, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] Hook before_agent.py execution started. ARGV: {sys.argv}\n")
    except Exception as e:
        log(f"Failed to write to hook_debug.log: {e}")

    try:
        # Load accounts list
        accounts = load_accounts()
        if not accounts:
            print("{}")
            sys.exit(0)

        # Find active account index
        active_idx = active_account_index(accounts)
        if active_idx is None:
            print("{}")
            sys.exit(0)

        active_acc = accounts[active_idx]
        email = active_acc.get("email") or active_acc.get("name") or f"Account {active_idx + 1}"

        # Check if the active account is blocked or low quota
        is_blocked = is_account_blocked_or_low(active_acc, accounts)
        try:
            debug_log = os.path.join(AGY_DIR, "brain/hook_debug.log")
            with open(debug_log, "a") as f:
                f.write(f"  [DEBUG] active_email: {email}, is_blocked: {is_blocked}\n")
        except:
            pass

        if is_blocked:
            log(f"Active account {email} has low quota or is blocked. Switching...")

            # 1. Mark the active account as blocked on disk ONLY if it is strictly blocked
            from switch import is_account_blocked_only
            if is_account_blocked_only(active_acc, accounts):
                if accounts[active_idx].get("status") != "🔴 Blocked":
                    accounts[active_idx]["status"] = "🔴 Blocked"
                    accounts[active_idx]["quota"] = "0%"
                    accounts[active_idx]["reset_info"] = "In 2h"
                    accounts[active_idx]["blocked_until"] = (datetime.now() + timedelta(hours=2)).isoformat()
                    accounts[active_idx]["last_checked"] = datetime.now().isoformat()
                    write_accounts(accounts, create_backup=False)

            # 2. Select replacement account
            found_idx = select_replacement_index(accounts, active_idx)
            if found_idx is not None:
                selected_acc = _write_active_account(accounts, found_idx)
                new_email = selected_acc.get("email") or selected_acc.get("name")

                # Delete token cache file if exists to force reload
                cache_file = Path(os.path.expanduser("~/.gemini/mcp-oauth-tokens-v2.json"))
                if cache_file.exists():
                    try:
                        cache_file.unlink()
                        log("Cleared token cache file.")
                    except OSError:
                        pass

                # 3. Save progress to .agy_progress.md
                log("Saving active conversation history...")
                try:
                    generate_quota_rollover()
                except Exception as ex_roll:
                    log(f"Failed to generate quota rollover: {ex_roll}")

                # 4. Touch reload/compaction signal file
                signal_file = Path(AGY_DIR) / ".compact_signal"
                try:
                    signal_file.touch()
                except Exception as ex_touch:
                    log(f"Failed to touch signal file: {ex_touch}")

                msg = (
                    f"⚡ **Tài khoản đã tự động xoay vòng** | Account Auto-Switched\n"
                    f"   Đã chuyển sang tài khoản mới: {new_email} do tài khoản cũ hết quota."
                )
                print(json.dumps({"systemMessage": msg}, ensure_ascii=False))

                # 5. Terminate agy-bin cleanly
                log("Killing ancestor agy-bin to trigger wrapper restart loop...")
                kill_ancestor_agy_bin()
                sys.exit(0)
            else:
                log("All accounts are low or blocked. Staying on current account.")
    except Exception as e:
        log(f"Error in BeforeAgent hook: {e}")

    print("{}")
    sys.exit(0)

if __name__ == "__main__":
    main()
