#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

# Add tools/agy/ directory to python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import AGY_DIR, TOKEN_FILE
from switch import is_account_blocked_or_low, select_replacement_index, _write_active_account
from storage import load_accounts, active_account_index

def log(message):
    print(f"[BeforeAgent] {message}", file=sys.stderr)

def main():
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
        if is_account_blocked_or_low(active_acc, accounts):
            log(f"Active account {email} has low quota or is blocked. Switching...")
            
            # Select replacement account
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
                
                msg = (
                    f"⚡ **Tài khoản đã tự động xoay vòng** | Account Auto-Switched\n"
                    f"   Đã chuyển sang tài khoản mới: {new_email} do tài khoản cũ hết quota."
                )
                print(json.dumps({"systemMessage": msg}, ensure_ascii=False))
                sys.exit(0)
            else:
                log("All accounts are low or blocked. Staying on current account.")
    except Exception as e:
        log(f"Error in BeforeAgent hook: {e}")
        
    print("{}")
    sys.exit(0)

if __name__ == "__main__":
    main()
