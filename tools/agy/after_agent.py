#!/usr/bin/env python3
import json
import os
import sys
import signal
from pathlib import Path
from datetime import datetime, timedelta

# Add tools/agy/ directory to python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import AGY_DIR, TOKEN_FILE
from switch import select_replacement_index, _write_active_account, JSON_FILE, is_account_blocked_or_low, generate_quota_rollover
from storage import load_accounts, active_account_index, write_accounts
from status_refresh import _check_single_account, _apply_status_result

def kill_ancestor_agy_bin():
    if os.environ.get("AGY_TESTING") == "1":
        return False
    pid = os.getpid()
    while pid > 1:
        try:
            # Read command and parent PID from proc fs
            with open(f"/proc/{pid}/stat", "r") as f:
                parts = f.read().split()
            ppid = int(parts[3])
            comm = parts[1].strip("()")
            
            # Check if this process is agy-bin
            if "agy-bin" in comm.lower():
                print(f"[AfterAgent] Found agy-bin ancestor (PID: {pid}). Terminating cleanly...", file=sys.stderr)
                os.kill(pid, signal.SIGTERM)
                return True
            pid = ppid
        except Exception:
            break
    return False

def log(message):
    print(f"[AfterAgent] {message}", file=sys.stderr)

def check_for_quota_error(text):
    text_lower = str(text).lower()
    return (
        "resource_exhausted" in text_lower
        or "quota exceeded" in text_lower
        or "429" in text_lower
        or "individual quota reached" in text_lower
        or "too many tokens" in text_lower
        or "rate limit" in text_lower
        or "exhausted" in text_lower
    )

def main():
    try:
        raw_input = sys.stdin.read()
        
        # Step 1: Check raw response text first for immediate errors
        had_immediate_error = False
        response_text = ""
        if raw_input.strip():
            try:
                data = json.loads(raw_input)
            except Exception:
                data = {}
            if isinstance(data, dict):
                for key in ["response", "text", "content", "agentResponse", "agent_response", "promptResponse"]:
                    if key in data:
                        response_text += str(data[key]) + "\n"
                if not response_text.strip():
                    response_text = raw_input
            else:
                response_text = str(raw_input)
            
            if check_for_quota_error(response_text):
                had_immediate_error = True
                log("Immediate quota error detected in agent response text.")

        # Step 2: Load accounts and find active account
        accounts = load_accounts()
        if not accounts:
            print("{}")
            sys.exit(0)
            
        active_idx = active_account_index(accounts)
        if active_idx is None:
            print("{}")
            sys.exit(0)
            
        active_acc = accounts[active_idx]
        email = active_acc.get("email") or active_acc.get("name") or f"Account {active_idx + 1}"
        
        # Load the original active token
        original_token = None
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, "r") as f:
                    original_token = json.load(f)
            except Exception:
                pass

        # Step 3: Perform live PTY quota check on the active account
        log(f"Running live quota check on active account {email} after response...")
        try:
            # Redirect stdout to stderr temporarily so status messages don't corrupt the JSON output
            old_stdout = sys.stdout
            sys.stdout = sys.stderr
            try:
                result = _check_single_account(
                    active_idx, 
                    active_acc, 
                    accounts, 
                    duplicate_tokens={}, 
                    active_email=email, 
                    original_token=original_token
                )
            finally:
                sys.stdout = old_stdout
            
            # Apply and save the fresh quota state to accounts.json
            _apply_status_result(accounts, result)
            write_accounts(accounts, create_backup=False)
            
            # Re-read active account with fresh quota values
            active_acc = accounts[active_idx]
            log(f"Live quota updated: {active_acc.get('quota')}")
        except Exception as check_exc:
            log(f"Warning: Live check failed: {check_exc}. Falling back to text check.")
            result = active_acc

        # Step 4: Evaluate if the active account is now blocked or low quota
        had_quota_exhaustion = is_account_blocked_or_low(active_acc, accounts)
        
        # Prioritize the remaining quota condition or the text-based error flag
        if had_immediate_error or had_quota_exhaustion:
            log(f"Active account {email} is blocked or low quota. Initiating switch...")
            
            # Block the active account if it wasn't blocked already
            if accounts[active_idx].get("status") != "🔴 Blocked":
                accounts[active_idx]["status"] = "🔴 Blocked"
                accounts[active_idx]["quota"] = "0%"
                accounts[active_idx]["reset_info"] = "In 2h"
                accounts[active_idx]["blocked_until"] = (datetime.now() + timedelta(hours=2)).isoformat()
                accounts[active_idx]["last_checked"] = datetime.now().isoformat()
                write_accounts(accounts, create_backup=False)
            
            # Select replacement account
            found_idx = select_replacement_index(accounts, active_idx)
            if found_idx is not None:
                selected_acc = _write_active_account(accounts, found_idx)
                new_email = selected_acc.get("email") or selected_acc.get("name")
                
                # Delete token cache file to force reload
                cache_file = Path(os.path.expanduser("~/.gemini/mcp-oauth-tokens-v2.json"))
                if cache_file.exists():
                    try:
                        cache_file.unlink()
                        log("Cleared token cache file.")
                    except OSError:
                        pass
                
                msg = (
                    f"🔄 **Hạn mức tài khoản sắp hết hoặc bị chặn!** | Quota warning/exhaustion.\n"
                    f"   Đang tự động chuyển sang tài khoản mới: {new_email} và thử lại..."
                )
                
                log("Saving active conversation history...")
                try:
                    generate_quota_rollover()
                except Exception as ex_roll:
                    log(f"Failed to generate quota rollover: {ex_roll}")

                # Touch the compaction signal file
                signal_file = Path(AGY_DIR) / ".compact_signal"
                try:
                    signal_file.touch()
                except Exception as ex_touch:
                    log(f"Failed to touch signal file: {ex_touch}")

                print(json.dumps({
                    "decision": "retry",
                    "systemMessage": msg
                }, ensure_ascii=False))
                
                log("Killing ancestor agy-bin to trigger wrapper restart loop...")
                kill_ancestor_agy_bin()
                sys.exit(0)
            else:
                log("All accounts are low or blocked. Staying on current account.")
    except Exception as e:
        log(f"Error in AfterAgent hook: {e}")
        
    print("{}")
    sys.exit(0)

if __name__ == "__main__":
    main()
