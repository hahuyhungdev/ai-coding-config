import os
import json
import re
import shutil
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from utils import (
    JSON_FILE, TOKEN_FILE, LOG_DIR, AGY_DIR, REAL_AGY,
    GEMINI_FALLBACK_MODEL, CLAUDE_FALLBACK_MODEL,
    get_username, ljust_display, format_cached_model_usage,
    account_display_name, account_key,
    format_exact_reset_time, parse_duration
)
from parser import (
    get_remaining_reset_from_logs, get_weekly_usage, parse_quota_output
)
from pty_client import get_quota_via_pty
from storage import write_accounts

def find_duplicate_refresh_tokens(accounts):
    """Map duplicate account indexes to the first account using that token."""
    first_seen = {}
    duplicates = {}
    for idx, account in enumerate(accounts):
        refresh_token = account.get("token", {}).get("refresh_token")
        if not refresh_token:
            continue
        if refresh_token in first_seen:
            duplicates[idx] = first_seen[refresh_token]
        else:
            first_seen[refresh_token] = idx
    return duplicates

def get_account_status():
    if not os.path.exists(JSON_FILE):
        print(f"❌ accounts.json not found at {JSON_FILE}")
        return

    with open(JSON_FILE, "r") as f:
        accounts = json.load(f)

    # Backup original active token
    orig_token = None
    active_email = None
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                orig_token = f.read()
                token_data = json.loads(orig_token)
                active_rt = token_data.get("token", {}).get("refresh_token")
                if active_rt:
                    for acc in accounts:
                        if acc.get("token", {}).get("refresh_token") == active_rt:
                            active_email = acc.get("email") or acc.get("name")
                            break
        except:
            pass

    duplicate_tokens = find_duplicate_refresh_tokens(accounts)

    def check_single_account(idx, acc):
        email = acc.get("email") or acc.get("name") or f"Account {idx}"

        if idx in duplicate_tokens:
            original_idx = duplicate_tokens[idx]
            return {
                "idx": idx,
                "email": email,
                "status": "🟡 Dup",
                "quota": f"Same as #{original_idx + 1}",
                "reset_info": "",
                "refreshed_token": None,
                "model_quotas": {},
                "blocked_until": None
            }

        # Print progress update
        print(f"⏳ Checking status for {email}...", flush=True)

        # Create sandbox directory
        sandbox_dir = os.path.join(AGY_DIR, f"scratch/sandbox_{idx}")
        sandbox_gemini_dir = os.path.join(sandbox_dir, ".gemini/antigravity-cli")
        os.makedirs(sandbox_gemini_dir, exist_ok=True)

        # Temporarily write this account token to sandbox
        sandbox_token_file = os.path.join(sandbox_gemini_dir, "antigravity-oauth-token")
        with open(sandbox_token_file, "w") as f:
            json.dump(acc, f)

        # Copy global cache directory to sandbox to bypass onboarding screen
        global_cache = os.path.join(AGY_DIR, "cache")
        if os.path.exists(global_cache):
            try:
                shutil.copytree(global_cache, os.path.join(sandbox_gemini_dir, "cache"))
            except Exception:
                pass

        # Run interactive PTY to fetch the real quota
        output = get_quota_via_pty(email, sandbox_dir=sandbox_dir)

        # Read refreshed token JSON from sandbox
        refreshed_token = None
        try:
            with open(sandbox_token_file, "r") as f:
                refreshed_acc = json.load(f)
                refreshed_token = refreshed_acc.get("token")
        except Exception:
            pass

        # Clean up sandbox directory
        try:
            shutil.rmtree(sandbox_dir)
        except Exception:
            pass

        status = "🔴 Blocked"
        reset_time_str = ""
        quota_str = "0%"
        model_quotas = {}

        if "Model Quota" in output or "Model Usage" in output or "Quota" in output or "GEMINI MODELS" in output or "CLAUDE AND GPT MODELS" in output:
            status = "🟢 Ready"
            quota_str = "100%"

            model_quotas = parse_quota_output(output)

            # Determine overall status from model_quotas
            if model_quotas:
                # Pick a representative model for the summary
                for rep_model in ["Gemini 3.5 Flash (Medium)", "Gemini 3.5 Flash (High)"]:
                    if rep_model in model_quotas:
                        q = model_quotas[rep_model]
                        if "weekly_pct" in q and "five_hour_pct" in q:
                            w_pct = q["weekly_pct"]
                            f_pct = q["five_hour_pct"]
                            quota_str = f"5H:{f_pct}%/W:{w_pct}%"
                            
                            w_ref = q.get("weekly_refresh", "")
                            f_ref = q.get("five_hour_refresh", "")
                            f_clean = format_exact_reset_time(f_ref) if f_ref else "Ready"
                            w_clean = format_exact_reset_time(w_ref) if w_ref else "Ready"
                            reset_time_str = f"5H:{f_clean}/W:{w_clean}"
                        else:
                            quota_str = f"{q['pct']}%"
                            if q['refresh']:
                                reset_time_str = format_exact_reset_time(q['refresh'])
                        break

                # Check if ALL models are at 0%
                all_zero = all(m["pct"] == 0 for m in model_quotas.values())
                if all_zero:
                    status = "🔴 Blocked"
                    quota_str = "0%"
        else:
            raw_reset = get_remaining_reset_from_logs(email, accounts)
            if raw_reset:
                status = "🔴 Blocked"
                quota_str = "🔴 0% (Blocked)"
                reset_time_str = f"5H:{format_exact_reset_time(raw_reset)}/W:Ready"
            else:
                # Assume it was ready but timed out / didn't show menu
                status = "🟢 Ready"
                quota_str = "100%" 

        # Calculate blocked_until timestamp
        from datetime import timedelta
        blocked_until_dt = None
        if status == "🔴 Blocked":
            if model_quotas:
                max_delta = timedelta(0)
                for q_item in model_quotas.values():
                    for ref_key in ["refresh", "weekly_refresh", "five_hour_refresh"]:
                        ref_val = q_item.get(ref_key, "")
                        if ref_val and ref_val.startswith("In "):
                            try:
                                d = parse_duration(ref_val.replace("In ", ""))
                                if d > max_delta:
                                    max_delta = d
                            except:
                                pass
                if max_delta.total_seconds() > 0:
                    blocked_until_dt = datetime.now() + max_delta
            elif 'raw_reset' in locals() and raw_reset:
                try:
                    d = parse_duration(raw_reset.replace("In ", ""))
                    if d.total_seconds() > 0:
                        blocked_until_dt = datetime.now() + d
                except:
                    pass

        is_active_label = " ⭐" if active_email and get_username(email) == get_username(active_email) else ""
        return {
            "idx": idx,
            "email": email + is_active_label,
            "status": status,
            "quota": quota_str,
            "reset_info": reset_time_str,
            "refreshed_token": refreshed_token,
            "model_quotas": model_quotas,
            "blocked_until": blocked_until_dt.isoformat() if blocked_until_dt else None
        }

    status_report = []

    try:
        # Run checks in parallel
        results = []
        workers = min(max(1, len(accounts) - len(duplicate_tokens)), 8)
        if workers > 0:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [
                    executor.submit(check_single_account, idx, acc)
                    for idx, acc in enumerate(accounts)
                ]
                for fut in futures:
                    results.append(fut.result())
        else:
            for idx, acc in enumerate(accounts):
                results.append(check_single_account(idx, acc))

        # Sort results by index to preserve original order
        results.sort(key=lambda x: x["idx"])

        for res in results:
            idx = res["idx"]
            status = res["status"]
            quota_str = res["quota"]
            reset_time_str = res["reset_info"]
            refreshed_token = res["refreshed_token"]
            model_quotas = res["model_quotas"]
            blocked_until_iso = res["blocked_until"]

            if refreshed_token:
                accounts[idx]["token"] = refreshed_token

            accounts[idx]["status"] = status
            accounts[idx]["quota"] = quota_str
            accounts[idx]["reset_info"] = reset_time_str
            accounts[idx]["last_checked"] = datetime.now().isoformat()
            if blocked_until_iso:
                accounts[idx]["blocked_until"] = blocked_until_iso
            elif "blocked_until" in accounts[idx]:
                del accounts[idx]["blocked_until"]

            accounts[idx]["model_quotas"] = model_quotas

            status_report.append({
                "index": idx,
                "email": res["email"],
                "status": status,
                "quota": quota_str,
                "reset_info": reset_time_str
            })

        # Save refreshed tokens back to accounts.json
        write_accounts(accounts, create_backup=False)

    finally:
        # Restore original active token
        if orig_token is not None:
            with open(TOKEN_FILE, "w") as f:
                f.write(orig_token)

    # Clear progress line
    print(" " * 80, end="\r", flush=True)

    # Display narrow table
    print("┌────┬──────────────────────┬──────────┬──────────────────┬────────────────────────────┐")
    print("│IDX │ ACCOUNT              │ STATUS   │ QUOTA            │ RESET TIME                 │")
    print("├────┼──────────────────────┼──────────┼──────────────────┼────────────────────────────┤")
    for row in status_report:
        idx_str = f"{row['index'] + 1}".center(4)

        raw_email = row['email']
        if len(raw_email) > 20:
            if " ⭐" in raw_email:
                email_str = raw_email[:18] + " ⭐"
            else:
                email_str = raw_email[:17] + "..."
        else:
            email_str = raw_email

        email_str_padded = ljust_display(email_str, 20)
        status_str_padded = ljust_display(row['status'], 8)
        quota_str_padded = ljust_display(row['quota'], 16)
        reset_str_padded = ljust_display(row['reset_info'], 26)

        print(f"│{idx_str}│ {email_str_padded} │ {status_str_padded} │ {quota_str_padded} │ {reset_str_padded} │")
    print("└────┴──────────────────────┴──────────┴──────────────────┴────────────────────────────┘")
    print("(* Quota shows account readiness. ⭐ indicates active account. 5H = 5-Hour Session Limit, W = Weekly Limit.)")

def list_accounts():
    if not os.path.exists(JSON_FILE):
        print(f"❌ accounts.json not found at {JSON_FILE}")
        return

    with open(JSON_FILE, "r") as f:
        accounts = json.load(f)

    if not accounts:
        print("❌ No accounts in accounts.json!")
        return

    # Find active account
    active_email = None
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                token_data = json.load(f)
                active_rt = token_data.get("token", {}).get("refresh_token")
                if active_rt:
                    for acc in accounts:
                        if acc.get("token", {}).get("refresh_token") == active_rt:
                            active_email = acc.get("email") or acc.get("name")
                            break
        except:
            pass

    print("┌─────┬──────────────────────┬──────────┬─────────────┬─────────────┐")
    print("│ IDX │ ACCOUNT              │ ACTIVE   │ GEMINI 5H/W │ OPUS 5H/W   │")
    print("├─────┼──────────────────────┼──────────┼─────────────┼─────────────┤")
    for idx, acc in enumerate(accounts):
        name = acc.get("email") or acc.get("name") or f"Account {idx}"
        idx_str = f"{idx + 1}".center(5)
        name_padded = ljust_display(name, 20)
        is_active = "⭐" if active_email and get_username(name) == get_username(active_email) else ""
        active_padded = ljust_display(is_active, 8)
        gemini_usage = format_cached_model_usage(acc, GEMINI_FALLBACK_MODEL)
        opus_usage = format_cached_model_usage(acc, CLAUDE_FALLBACK_MODEL)
        gemini_padded = ljust_display(gemini_usage, 11)
        opus_padded = ljust_display(opus_usage, 11)
        print(f"│{idx_str}│ {name_padded} │ {active_padded} │ {gemini_padded} │ {opus_padded} │")
    print("└─────┴──────────────────────┴──────────┴─────────────┴─────────────┘")
    print("Gemini = Gemini 3.5 Flash (High); Opus = Claude Opus 4.6 (Thinking).")
    print("5H/W = 5-Hour Session Limit / Weekly Limit. '?' means run 'agy status' to refresh.")

def show_weekly_usage(days=7):
    rows = get_weekly_usage(days=days)
    print(f"Local {days}-day usage estimate from Antigravity CLI logs")
    print("Counts local sessions and user prompts, not provider billing or official quota.")
    print("┌──────────────────────┬──────┬─────────┬────────┬────────┬──────┐")
    print("│ ACCOUNT              │ SESS │ PROMPTS │ GEMINI │ OPUS   │ ERR  │")
    print("├──────────────────────┼──────┼─────────┼────────┼────────┼──────┤")
    for row in rows:
        account = row["account"]
        if len(account) > 20:
            account = account[:17] + "..."
        account_padded = ljust_display(account, 20)
        sessions = str(row["sessions"]).center(4)
        prompts = str(row["prompts"]).center(7)
        gemini = str(row["gemini_prompts"]).center(6)
        opus = str(row["opus_prompts"]).center(6)
        errors = str(row["quota_errors"]).center(4)
        print(f"│ {account_padded} │ {sessions} │ {prompts} │ {gemini} │ {opus} │ {errors} │")
    print("└──────────────────────┴──────┴─────────┴────────┴────────┴──────┘")
    print("Gemini/Opus columns are prompt counts attributed to the last selected model in each session.")

def select_account(target):
    if not os.path.exists(JSON_FILE):
        print(f"❌ accounts.json not found at {JSON_FILE}")
        return

    with open(JSON_FILE, "r") as f:
        accounts = json.load(f)

    if not accounts:
        print("❌ No accounts in accounts.json!")
        return

    matched_idx = None
    if target.isdigit():
        idx = int(target) - 1  # User-facing indexes are 1-based
        if 0 <= idx < len(accounts):
            matched_idx = idx
        else:
            print(f"❌ Index {target} out of range (1 to {len(accounts)}).")
            return
    else:
        target_lower = target.lower()
        matches = []
        for idx, acc in enumerate(accounts):
            email = acc.get("email") or acc.get("name") or ""
            if target_lower in email.lower():
                matches.append((idx, email))
        
        if len(matches) == 0:
            print(f"❌ No account found matching: '{target}'")
            return
        elif len(matches) > 1:
            print(f"⚠️ Multiple accounts matched '{target}':")
            for idx, email in matches:
                print(f"  [{idx}] {email}")
            print("Please specify a more precise email or use the index.")
            return
        else:
            matched_idx = matches[0][0]

    # Write selected account to token file
    selected_acc = accounts[matched_idx]
    with open(TOKEN_FILE, "w") as f:
        json.dump(selected_acc, f)

    # Update index for next rotation
    next_index = (matched_idx + 1) % len(accounts)
    INDEX_FILE = os.path.join(AGY_DIR, ".current_index")
    with open(INDEX_FILE, "w") as f:
        f.write(str(next_index))

    email = selected_acc.get("email") or selected_acc.get("name") or f"Account {matched_idx}"
    print(f"🟢 Switched active account to: {email} (Index: [{matched_idx + 1}])")

def remove_account(target=None):
    if not os.path.exists(JSON_FILE):
        print(f"❌ accounts.json not found at {JSON_FILE}")
        return

    with open(JSON_FILE, "r") as f:
        accounts = json.load(f)

    if not accounts:
        print("❌ No accounts in accounts.json!")
        return

    if target is None:
        print("\n👥 Available Accounts:")
        print("┌─────┬──────────────────────┐")
        print("│ IDX │ ACCOUNT NAME         │")
        print("├─────┼──────────────────────┤")
        for idx, acc in enumerate(accounts):
            name = acc.get("email") or acc.get("name") or f"Account {idx}"
            idx_str = f"{idx + 1}".center(5)
            name_padded = name.ljust(20)[:20]
            print(f"│{idx_str}│ {name_padded} │")
        print("└─────┴──────────────────────┘")
        print("To remove, run: agy remove-account <idx> or agy remove-account <email_or_name>")
        return

    matched_idx = None
    if target.isdigit():
        idx = int(target) - 1
        if 0 <= idx < len(accounts):
            matched_idx = idx
        else:
            print(f"❌ Index {target} out of range (1 to {len(accounts)}).")
            return
    else:
        target_lower = target.lower()
        matches = []
        for idx, acc in enumerate(accounts):
            email = acc.get("email") or acc.get("name") or ""
            if target_lower in email.lower():
                matches.append((idx, email))

        if len(matches) == 0:
            print(f"❌ No account found matching: '{target}'")
            return
        elif len(matches) > 1:
            print(f"⚠️ Multiple accounts matched '{target}':")
            for idx, email in matches:
                print(f"  [{idx}] {email}")
            print("Please specify a more precise email or use the index.")
            return
        else:
            matched_idx = matches[0][0]

    removed_acc = accounts.pop(matched_idx)
    removed_name = removed_acc.get("email") or removed_acc.get("name") or f"Account {matched_idx}"

    write_accounts(accounts)

    print(f"🗑️ Successfully removed account: {removed_name} (Index: [{matched_idx}])")

    INDEX_FILE = os.path.join(AGY_DIR, ".current_index")
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, "r") as f:
                curr_idx = int(f.read().strip())
            if curr_idx >= len(accounts):
                new_idx = 0
            else:
                new_idx = curr_idx
            with open(INDEX_FILE, "w") as f:
                f.write(str(new_idx))
        except:
            pass

def import_current_token(custom_email=None):
    if not os.path.exists(TOKEN_FILE):
        print(f"❌ No active token file found at {TOKEN_FILE}")
        print("Please log in or run 'agy' first to generate a token.")
        return

    try:
        with open(TOKEN_FILE, "r") as f:
            current_data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to parse token file: {e}")
        return

    email = custom_email or current_data.get("email")
    if not email:
        print("⏳ Auto-detecting email from active session...")
        subprocess.run([REAL_AGY, "-p", "ping connection check - say pong"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        log_files = []
        if os.path.exists(LOG_DIR):
            for f in os.listdir(LOG_DIR):
                if f.startswith("cli-") and f.endswith(".log"):
                    path = os.path.join(LOG_DIR, f)
                    log_files.append((path, os.path.getmtime(path)))
        log_files.sort(key=lambda x: x[1], reverse=True)
        
        if log_files:
            latest_log = log_files[0][0]
            try:
                with open(latest_log, "r", errors="ignore") as lf:
                    for _ in range(200):
                        line = lf.readline()
                        if not line:
                            break
                        if "applyAuthResult" in line and "email=" in line:
                            m = re.search(r"email=([^,\s]+)", line)
                            if m:
                                email = m.group(1)
                                break
            except:
                pass
                
    if not email:
        print("❌ Could not auto-detect email. Please specify your account name:")
        print("   agy add-current <email_or_name>")
        return

    username = get_username(email)

    accounts = []
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r") as f:
                accounts = json.load(f)
        except Exception:
            pass

    updated = False
    for idx, acc in enumerate(accounts):
        acc_email = acc.get("email") or acc.get("name") or ""
        if get_username(acc_email) == username:
            accounts[idx]["token"] = current_data.get("token") or current_data
            accounts[idx]["auth_method"] = current_data.get("auth_method", "consumer")
            if "@" in email:
                accounts[idx]["email"] = email
            updated = True
            break

    if not updated:
        accounts.append({
            "email": email if "@" in email else username,
            "label": None if "@" in email else username,
            "auth_method": current_data.get("auth_method", "consumer"),
            "token": current_data.get("token") or current_data
        })
        print(f"🟢 Successfully added new account '{username}' to accounts.json!")
    else:
        print(f"🟢 Successfully updated existing account '{username}' in accounts.json!")

    write_accounts(accounts)

def clean_conversations():
    # Read history.jsonl to find active conversation IDs
    history_file = os.path.join(AGY_DIR, "history.jsonl")
    active_uuids = set()
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            cid = data.get("conversationId")
                            if cid:
                                active_uuids.add(cid)
                        except:
                            pass
        except Exception as e:
            print(f"❌ Error reading history.jsonl: {e}")
            return

    # Scan conversations/ directory for .db and .pb files
    convs_dir = os.path.join(AGY_DIR, "conversations")
    brain_dir = os.path.join(AGY_DIR, "brain")
    
    cleaned_count = 0
    total_saved_bytes = 0
    
    # Check database/pb files
    if os.path.exists(convs_dir):
        for f in os.listdir(convs_dir):
            if f.endswith(".db") or f.endswith(".pb"):
                uuid = f.split(".")[0]
                if uuid not in active_uuids:
                    fpath = os.path.join(convs_dir, f)
                    try:
                        fsize = os.path.getsize(fpath)
                        os.remove(fpath)
                        cleaned_count += 1
                        total_saved_bytes += fsize
                    except Exception as e:
                        print(f"⚠️ Failed to remove {f}: {e}")
                        
    # Check brain directories
    if os.path.exists(brain_dir):
        for d in os.listdir(brain_dir):
            if re.match(r"^[0-9a-fA-F-]{36}$", d):
                if d not in active_uuids:
                    dpath = os.path.join(brain_dir, d)
                    try:
                        dsize = sum(os.path.getsize(os.path.join(dirpath, filename)) 
                                    for dirpath, dirnames, filenames in os.walk(dpath) 
                                    for filename in filenames)
                        shutil.rmtree(dpath)
                        total_saved_bytes += dsize
                    except Exception as e:
                        print(f"⚠️ Failed to remove directory {d}: {e}")

    mb_saved = total_saved_bytes / (1024 * 1024)
    print(f"🧹 Cleaned up {cleaned_count} automated/orphaned sessions.")
    print(f"💾 Saved {mb_saved:.2f} MB of disk space.")

def delete_conversation(target=None):
    history_file = os.path.join(AGY_DIR, "history.jsonl")
    if not os.path.exists(history_file):
        print("❌ history.jsonl not found.")
        return

    # Read history entries
    history_entries = []
    try:
        with open(history_file, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        if data.get("conversationId"):
                            history_entries.append(data)
                    except:
                        pass
    except Exception as e:
        print(f"❌ Error reading history.jsonl: {e}")
        return

    if not history_entries:
        print("ℹ️ No conversations found in history.")
        return

    unique_convs = {}
    for entry in history_entries:
        cid = entry["conversationId"]
        unique_convs[cid] = entry

    sorted_convs = sorted(unique_convs.values(), key=lambda x: x.get("timestamp", 0))

    if target is None:
        print("\n💬 Available Conversations:")
        print("┌─────┬──────────────────────────────────────┬──────────────────────────────────────────┐")
        print("│ IDX │ CONVERSATION ID                      │ LATEST PROMPT                            │")
        print("├─────┼──────────────────────────────────────┼──────────────────────────────────────────┤")
        for idx, conv in enumerate(sorted_convs):
            cid = conv["conversationId"]
            display = conv.get("display", "").replace("\n", " ")
            if len(display) > 40:
                display = display[:37] + "..."
            idx_str = f"{idx + 1}".center(5)
            display_padded = display.ljust(40)[:40]
            print(f"│{idx_str}│ {cid} │ {display_padded} │")
        print("└─────┴──────────────────────────────────────┴──────────────────────────────────────────┘")
        print("To delete, run: agy delete <idx> or agy delete <conversation_id>")
        return

    selected_cid = None
    if target.isdigit():
        idx = int(target) - 1
        if 0 <= idx < len(sorted_convs):
            selected_cid = sorted_convs[idx]["conversationId"]
        else:
            print(f"❌ Index {target} out of range (1 to {len(sorted_convs)}).")
            return
    else:
        if re.match(r"^[0-9a-fA-F-]{36}$", target):
            selected_cid = target
        else:
            matches = []
            for idx, conv in enumerate(sorted_convs):
                if target.lower() in conv.get("display", "").lower():
                    matches.append(conv)
            if len(matches) == 0:
                print(f"❌ No conversation found matching: '{target}'")
                return
            elif len(matches) > 1:
                print(f"⚠️ Multiple conversations matched '{target}':")
                for m in matches:
                    print(f"  {m['conversationId']} - {m.get('display')}")
                return
            else:
                selected_cid = matches[0]["conversationId"]

    deleted_files = 0
    convs_dir = os.path.join(AGY_DIR, "conversations")
    brain_dir = os.path.join(AGY_DIR, "brain")

    for ext in [".db", ".pb"]:
        fpath = os.path.join(convs_dir, f"{selected_cid}{ext}")
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
                deleted_files += 1
            except Exception as e:
                print(f"⚠️ Failed to delete file {fpath}: {e}")

    dpath = os.path.join(brain_dir, selected_cid)
    if os.path.exists(dpath):
        try:
            shutil.rmtree(dpath)
            deleted_files += 1
        except Exception as e:
            print(f"⚠️ Failed to delete directory {dpath}: {e}")

    try:
        new_lines = []
        with open(history_file, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        if data.get("conversationId") != selected_cid:
                            new_lines.append(line)
                    except:
                        new_lines.append(line)
        with open(history_file, "w") as f:
            f.writelines(new_lines)
    except Exception as e:
        print(f"⚠️ Failed to update history.jsonl: {e}")

    print(f"🗑️ Successfully deleted conversation {selected_cid}.")

def add_token_from_input(custom_email=None):
    print("📋 Paste your token JSON below, then press Ctrl+D (Linux/Mac) or Ctrl+Z (Windows):")
    print()

    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass

    raw = "\n".join(lines).strip()
    if not raw:
        print("❌ No input received.")
        return

    try:
        token_data = json.loads(raw)
    except Exception as e:
        print(f"❌ Invalid JSON: {e}")
        return

    accounts = []
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r") as f:
                accounts = json.load(f)
        except Exception:
            pass

    if "token" in token_data and isinstance(token_data["token"], dict):
        token_obj = token_data["token"]
        auth_method = token_data.get("auth_method", "consumer")
        email = custom_email or token_data.get("email")
    elif "refresh_token" in token_data:
        token_obj = token_data
        auth_method = "consumer"
        email = custom_email
    else:
        print("❌ Invalid token. Expected JSON with 'refresh_token' or 'token' key.")
        return

    if not token_obj.get("refresh_token"):
        print("❌ No refresh_token found in the JSON.")
        return

    if not email:
        email = input("📧 Enter account name/email label: ").strip()
        if not email:
            email = "account-" + str(len(accounts))
            print(f"⏳ Using default label: '{email}'")

    username = get_username(email)

    updated = False
    for idx, acc in enumerate(accounts):
        acc_email = acc.get("email") or acc.get("name") or ""
        if get_username(acc_email) == username:
            accounts[idx]["token"] = token_obj
            accounts[idx]["auth_method"] = auth_method
            updated = True
            break

    if not updated:
        accounts.append({
            "email": username,
            "auth_method": auth_method,
            "token": token_obj
        })
        print(f"\n🟢 Added new account '{username}'!")
    else:
        print(f"\n🟢 Updated existing account '{username}'!")

    write_accounts(accounts)

    print(f"   Total accounts: {len(accounts)}")

def import_from_file(file_path, custom_email=None):
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    try:
        with open(file_path, "r") as f:
            token_data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to parse JSON: {e}")
        return

    accounts = []
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r") as f:
                accounts = json.load(f)
        except Exception:
            pass

    if "token" in token_data and isinstance(token_data["token"], dict):
        token_obj = token_data["token"]
        auth_method = token_data.get("auth_method", "consumer")
        email = custom_email or token_data.get("email")
    elif "refresh_token" in token_data:
        token_obj = token_data
        auth_method = "consumer"
        email = custom_email
    else:
        print("❌ Invalid token file. Expected JSON with 'refresh_token' or 'token' key.")
        return

    if not token_obj.get("refresh_token"):
        print("❌ No refresh_token found in the file.")
        return

    if not email:
        basename = os.path.splitext(os.path.basename(file_path))[0]
        email = basename
        print(f"⏳ No email specified, using filename as label: '{email}'")

    username = get_username(email)

    updated = False
    for idx, acc in enumerate(accounts):
        acc_email = acc.get("email") or acc.get("name") or ""
        if get_username(acc_email) == username:
            accounts[idx]["token"] = token_obj
            accounts[idx]["auth_method"] = auth_method
            updated = True
            break

    if not updated:
        accounts.append({
            "email": username,
            "auth_method": auth_method,
            "token": token_obj
        })
        print(f"🟢 Added new account '{username}' from {os.path.basename(file_path)}!")
    else:
        print(f"🟢 Updated existing account '{username}' with token from {os.path.basename(file_path)}!")

    write_accounts(accounts)

    print(f"   Total accounts: {len(accounts)}")
