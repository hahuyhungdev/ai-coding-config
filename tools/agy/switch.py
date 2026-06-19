import os
import json
import re
import sys
import time
from datetime import datetime, timedelta
from utils import (
    JSON_FILE, TOKEN_FILE, LOG_DIR, AGY_DIR,
    GEMINI_FALLBACK_MODEL, CLAUDE_FALLBACK_MODEL,
    GEMINI_MODELS, CLAUDE_MODELS,
    get_username, parse_duration, parse_log_timestamp,
    get_model_pct, format_exact_reset_time, remaining_quota_value
)
from parser import get_remaining_reset_from_logs

def has_model_quota(acc, model_name, threshold=30):
    return get_model_pct(acc.get("model_quotas", {}), model_name) > threshold

def model_group_exhausted(model_quotas, model_names, threshold=30):
    present = [name for name in model_names if name in model_quotas]
    return bool(present) and all(get_model_pct(model_quotas, name) <= threshold for name in present)

def choose_same_account_fallback(acc, blocked_model=""):
    """Prefer Gemini first, then Claude Opus; never fall back from Claude to Gemini."""
    model_quotas = acc.get("model_quotas", {})

    if blocked_model == "gemini":
        if not model_quotas or has_model_quota(acc, CLAUDE_FALLBACK_MODEL):
            return CLAUDE_FALLBACK_MODEL
        return ""

    if blocked_model == "claude":
        return ""

    if model_quotas:
        if has_model_quota(acc, GEMINI_FALLBACK_MODEL):
            return GEMINI_FALLBACK_MODEL

        gemini_exhausted = model_group_exhausted(model_quotas, GEMINI_MODELS)
        opus_available = has_model_quota(acc, CLAUDE_FALLBACK_MODEL)
        claude_exhausted = model_group_exhausted(model_quotas, [CLAUDE_FALLBACK_MODEL])

        if gemini_exhausted and opus_available:
            return CLAUDE_FALLBACK_MODEL
        if claude_exhausted:
            return ""

    return ""

def is_account_blocked_or_low(acc, accounts):
    email = acc.get("email") or acc.get("name")
    if not email:
        return True
    
    # 1. Real-time log check (most accurate for active blocks)
    reset_time = get_remaining_reset_from_logs(email, accounts)
    if reset_time:
        return True
        
    # 2. Check cached status & quota
    status = acc.get("status")
    if status == "🔴 Blocked":
        # Check if the block has expired (prefer blocked_until timestamp)
        blocked_until_str = acc.get("blocked_until")
        if blocked_until_str:
            try:
                blocked_until = datetime.fromisoformat(blocked_until_str)
                if datetime.now() < blocked_until:
                    return True # Still blocked
                else:
                    return False # Block has expired, assume ready
            except:
                return True

        # Fallback for backwards compatibility
        last_checked_str = acc.get("last_checked")
        reset_info = acc.get("reset_info", "")
        if last_checked_str and reset_info and reset_info.startswith("In "):
            try:
                last_checked = datetime.fromisoformat(last_checked_str)
                duration = parse_duration(reset_info[3:])
                blocked_until = last_checked + duration
                if datetime.now() < blocked_until:
                    return True # Still blocked
                else:
                    return False # Block has expired, assume ready
            except:
                return True
        else:
            return True
            
    # Check cached quota percentage
    quota_val = acc.get("quota")
    if quota_val:
        pct = remaining_quota_value(quota_val)
        if pct != -1 and pct <= 30:  # Switch when quota is running low (<= 30%)
            return True

    return False

def check_last_log_for_quota_error():
    """Quick check: did the MOST RECENT agy session fail with a quota error?
    Returns (had_error, reset_time_str, blocked_model) where:
      - had_error: True if quota error found
      - reset_time_str: e.g. "In 2h30m"
      - blocked_model: "gemini" or "claude" or "unknown"
    """
    if not os.path.exists(LOG_DIR):
        return False, "", ""

    log_files = []
    for f in os.listdir(LOG_DIR):
        if f.startswith("cli-") and f.endswith(".log"):
            path = os.path.join(LOG_DIR, f)
            log_files.append((path, os.path.getmtime(path)))
    if not log_files:
        return False, "", ""

    log_files.sort(key=lambda x: x[1], reverse=True)
    latest_log = log_files[0][0]

    # Only check logs modified in the last 15 minutes (recent session)
    if datetime.fromtimestamp(log_files[0][1]) < datetime.now() - timedelta(minutes=15):
        return False, "", ""

    try:
        with open(latest_log, "r", errors="ignore") as f:
            lines = f.readlines()

        # Step 1: Find which model was being used (look for model label from the bottom of log)
        blocked_model = "unknown"
        for line in reversed(lines):
            m = re.search(r'label="([^"]+)"', line)
            if m:
                label = m.group(1).lower()
                if "claude" in label:
                    blocked_model = "claude"
                elif "gemini" in label:
                    blocked_model = "gemini"
                break

        # Step 2: Scan lines for quota error
        for line in reversed(lines):
            line_lower = line.lower()
            if (
                "resource_exhausted" in line_lower
                or "quota exceeded" in line_lower
                or "429" in line_lower
                or "individual quota reached" in line_lower
                or "too many tokens" in line_lower
                or "rate limit" in line_lower
            ):
                m = re.search(r"resets in\s*([0-9hms]+)", line, re.IGNORECASE)
                reset_str = ""
                if m:
                    reset_str = "In " + m.group(1)
                return True, reset_str, blocked_model
    except Exception:
        pass

    return False, "", ""

def get_model_suggestion(acc, blocked_model=""):
    """Check per-model quota cached in accounts.json and suggest an available model.
    Returns model label string or empty string if no suggestion.
    """
    return choose_same_account_fallback(acc, blocked_model=blocked_model)

def auto_switch_account(quiet=False):
    if not os.path.exists(JSON_FILE):
        if not quiet:
            print(f"❌ accounts.json not found at {JSON_FILE}")
        return ""

    with open(JSON_FILE, "r") as f:
        accounts = json.load(f)

    if not accounts:
        if not quiet:
            print("❌ No accounts in accounts.json!")
        return ""

    # Find active account index
    active_idx = None
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                token_data = json.load(f)
                active_rt = token_data.get("token", {}).get("refresh_token")
                if active_rt:
                    for idx, acc in enumerate(accounts):
                        if acc.get("token", {}).get("refresh_token") == active_rt:
                            active_idx = idx
                            break
        except:
            pass

    if active_idx is None:
        active_idx = 0
        selected_acc = accounts[0]
        with open(TOKEN_FILE, "w") as f:
            json.dump(selected_acc, f)
        if os.name == 'posix':
            try:
                os.chmod(TOKEN_FILE, 0o600)
            except OSError:
                pass
        email = selected_acc.get("email") or selected_acc.get("name") or "Account 1"
        if not quiet:
            print(f"🔄 Initialized active account to: {email}")
        return ""

    active_acc = accounts[active_idx]
    active_email = active_acc.get("email") or active_acc.get("name") or f"Account {active_idx + 1}"

    if is_account_blocked_or_low(active_acc, accounts):
        if not quiet:
            print(f"⚠️ Current account '{active_email}' is blocked or has low quota (<=30%). Searching for replacement...")

        # Search for healthy candidate with the highest remaining quota
        found_idx = None
        best_idx = None
        best_quota = -2
        for i in range(1, len(accounts)):
            candidate_idx = (active_idx + i) % len(accounts)
            candidate_acc = accounts[candidate_idx]
            candidate_email = candidate_acc.get("email") or candidate_acc.get("name") or f"Account {candidate_idx + 1}"
            
            if not quiet:
                print(f"  🔍 Checking candidate: {candidate_email}...", end="\r", flush=True)
                time.sleep(0.12)
            
            if not is_account_blocked_or_low(candidate_acc, accounts):
                q_val = remaining_quota_value(candidate_acc.get("quota"))
                if q_val > best_quota:
                    best_quota = q_val
                    best_idx = candidate_idx
                if not quiet:
                    print(f"  ✅ Eligible (quota {q_val}%): {candidate_email}      ", flush=True)
            else:
                if not quiet:
                    print(f"  ❌ Skipped (low quota/blocked): {candidate_email}      ", flush=True)

        if best_idx is not None:
            found_idx = best_idx
            best_email = accounts[best_idx].get("email") or accounts[best_idx].get("name") or f"Account {best_idx + 1}"
            if not quiet:
                print(f"  ✅ Selected replacement with highest quota ({best_quota}%): {best_email}!      ", flush=True)

        if found_idx is not None:
            # Switch to this account!
            selected_acc = accounts[found_idx]
            with open(TOKEN_FILE, "w") as f:
                json.dump(selected_acc, f)
            if os.name == 'posix':
                try:
                    os.chmod(TOKEN_FILE, 0o600)
                except OSError:
                    pass

            INDEX_FILE = os.path.join(AGY_DIR, ".current_index")
            with open(INDEX_FILE, "w") as f:
                f.write(str((found_idx + 1) % len(accounts)))

            new_email = selected_acc.get("email") or selected_acc.get("name")
            quota = selected_acc.get("quota", "?")
            reset_info = selected_acc.get("reset_info", "")
            quota_str = f" - Quota: {quota}"
            if reset_info:
                quota_str += f" ({reset_info})"
            print(f"🔄 Auto-switched account to: {new_email} (Index: [{found_idx + 1}]){quota_str}")

            # Suggest model for the newly switched account if needed
            suggestion = get_model_suggestion(selected_acc)
            if suggestion:
                print(f"MODEL:{suggestion}")
                return suggestion
        else:
            # All accounts are low or blocked. Try model fallback on the current account.
            _, _, blocked_model = check_last_log_for_quota_error()
            if not blocked_model or blocked_model == "unknown":
                blocked_model = active_acc.get("last_blocked_model", "")

            suggestion = get_model_suggestion(active_acc, blocked_model=blocked_model)
            if suggestion:
                print(f"MODEL:{suggestion}")
                return suggestion

            if not quiet:
                print("⚠️ All accounts are currently blocked or low on quota! Staying on the current account.")
    else:
        had_error, _, blocked_model = check_last_log_for_quota_error()
        if had_error and blocked_model and blocked_model != "unknown":
            suggestion = get_model_suggestion(active_acc, blocked_model=blocked_model)
            if suggestion:
                print(f"MODEL:{suggestion}")
                return suggestion

        model_quotas = active_acc.get("model_quotas", {})
        if model_quotas:
            suggestion = get_model_suggestion(active_acc)
            if suggestion:
                print(f"MODEL:{suggestion}")
                return suggestion

    return ""

def post_check_and_switch():
    had_quota_error, reset_time, blocked_model = check_last_log_for_quota_error()
    if not had_quota_error:
        sys.exit(1)

    print(f"⚠️ Quota exhausted on {blocked_model} model! {reset_time}")

    if not os.path.exists(JSON_FILE):
        sys.exit(1)

    with open(JSON_FILE, "r") as f:
        accounts = json.load(f)

    active_idx = None
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                token_data = json.load(f)
                active_rt = token_data.get("token", {}).get("refresh_token")
                if active_rt:
                    for idx, acc in enumerate(accounts):
                        if acc.get("token", {}).get("refresh_token") == active_rt:
                            active_idx = idx
                            break
        except:
            pass

    if active_idx is not None:
        accounts[active_idx]["status"] = "🔴 Blocked"
        accounts[active_idx]["quota"] = "0%"
        if reset_time:
            accounts[active_idx]["reset_info"] = format_exact_reset_time(reset_time)
            try:
                d = parse_duration(reset_time.replace("In ", ""))
                if d.total_seconds() > 0:
                    accounts[active_idx]["blocked_until"] = (datetime.now() + d).isoformat()
            except:
                pass
        else:
            accounts[active_idx]["reset_info"] = "In 2h"
            accounts[active_idx]["blocked_until"] = (datetime.now() + timedelta(hours=2)).isoformat()
        accounts[active_idx]["last_checked"] = datetime.now().isoformat()
        with open(JSON_FILE, "w") as f:
            json.dump(accounts, f, indent=2)
        if os.name == 'posix':
            try:
                os.chmod(JSON_FILE, 0o600)
            except OSError:
                pass

    if active_idx is None:
        active_idx = 0

    found_idx = None
    best_idx = None
    best_quota = -2
    for i in range(1, len(accounts)):
        candidate_idx = (active_idx + i) % len(accounts)
        candidate_acc = accounts[candidate_idx]
        candidate_email = candidate_acc.get("email") or candidate_acc.get("name") or f"Account {candidate_idx + 1}"
        
        print(f"  🔍 Checking candidate: {candidate_email}...", end="\r", flush=True)
        time.sleep(0.12)
        
        if not is_account_blocked_or_low(candidate_acc, accounts):
            q_val = remaining_quota_value(candidate_acc.get("quota"))
            if q_val > best_quota:
                best_quota = q_val
                best_idx = candidate_idx
            print(f"  ✅ Eligible (quota {q_val}%): {candidate_email}      ", flush=True)
        else:
            print(f"  ❌ Skipped (low quota/blocked): {candidate_email}      ", flush=True)

    if best_idx is not None:
        found_idx = best_idx
        best_email = accounts[best_idx].get("email") or accounts[best_idx].get("name") or f"Account {best_idx + 1}"
        print(f"  ✅ Selected replacement with highest quota ({best_quota}%): {best_email}!      ", flush=True)

    if found_idx is not None:
        selected_acc = accounts[found_idx]
        with open(TOKEN_FILE, "w") as f:
            json.dump(selected_acc, f)
        if os.name == 'posix':
            try:
                os.chmod(TOKEN_FILE, 0o600)
            except OSError:
                pass

        INDEX_FILE = os.path.join(AGY_DIR, ".current_index")
        with open(INDEX_FILE, "w") as f:
            f.write(str((found_idx + 1) % len(accounts)))

        new_email = selected_acc.get("email") or selected_acc.get("name")
        quota = selected_acc.get("quota", "?")
        reset_info = selected_acc.get("reset_info", "")
        quota_str = f" - Quota: {quota}"
        if reset_info:
            quota_str += f" ({reset_info})"
        generate_quota_rollover()
        print(f"🔄 Switched to: {new_email} (Index: [{found_idx + 1}]){quota_str} — retrying...")
        print("SWITCH_ACCOUNT")
        sys.exit(0)
    else:
        # No healthy replacement account found. Try same-account model fallback.
        if blocked_model == "gemini":
            fallback_model = CLAUDE_FALLBACK_MODEL
            fallback_label = "claude"
        else:
            fallback_model = None
            fallback_label = None

        if fallback_model:
            generate_quota_rollover()
            print(f"🔄 Trying {fallback_label} model on same account...")
            print(f"SWITCH_MODEL:{fallback_model}")
            sys.exit(0)

        print("❌ All accounts are blocked! Cannot retry.")
        sys.exit(2)

def rotate_account():
    if not os.path.exists(JSON_FILE):
        print(f"❌ accounts.json not found at {JSON_FILE}")
        return

    with open(JSON_FILE, "r") as f:
        accounts = json.load(f)

    if not accounts:
        print("❌ No accounts in accounts.json!")
        return

    active_idx = None
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                token_data = json.load(f)
                active_rt = token_data.get("token", {}).get("refresh_token")
                if active_rt:
                    for idx, acc in enumerate(accounts):
                        if acc.get("token", {}).get("refresh_token") == active_rt:
                            active_idx = idx
                            break
        except:
            pass

    if active_idx is None:
        next_idx = 0
    else:
        next_idx = (active_idx + 1) % len(accounts)

    selected_acc = accounts[next_idx]
    with open(TOKEN_FILE, "w") as f:
        json.dump(selected_acc, f)
    if os.name == 'posix':
        try:
            os.chmod(TOKEN_FILE, 0o600)
        except OSError:
            pass

    INDEX_FILE = os.path.join(AGY_DIR, ".current_index")
    with open(INDEX_FILE, "w") as f:
        f.write(str((next_idx + 1) % len(accounts)))

    email = selected_acc.get("email") or selected_acc.get("name") or f"Account {next_idx + 1}"
    quota = selected_acc.get("quota", "?")
    reset_info = selected_acc.get("reset_info", "")
    quota_str = f" - Quota: {quota}"
    if reset_info:
        quota_str += f" ({reset_info})"
    print(f"🔄 Manually rotated active account to: {email} (Index: [{next_idx + 1} / {len(accounts)}]){quota_str}")


def generate_quota_rollover():
    brain_dir = os.path.expanduser("~/.gemini/antigravity-cli/brain")
    if not os.path.exists(brain_dir):
        return
        
    subdirs = []
    for d in os.listdir(brain_dir):
        path = os.path.join(brain_dir, d)
        if os.path.isdir(path) and not d.startswith("."):
            try:
                subdirs.append((path, os.path.getmtime(path)))
            except OSError:
                pass
            
    if not subdirs:
        return
        
    subdirs.sort(key=lambda x: x[1], reverse=True)
    latest_session_dir = subdirs[0][0]
    
    transcript_path = os.path.join(latest_session_dir, ".system_generated/logs/transcript.jsonl")
    if not os.path.exists(transcript_path):
        return
        
    # Read the transcript and extract the last few turns
    turns = []
    try:
        with open(transcript_path, "r", errors="ignore") as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                step_type = data.get("type")
                content = data.get("content")
                if not content:
                    continue
                if step_type == "USER_INPUT":
                    # Remove XML tags if present
                    clean_content = content
                    m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", content, re.DOTALL)
                    if m:
                        clean_content = m.group(1).strip()
                    turns.append(f"User: {clean_content}")
                elif step_type == "PLANNER_RESPONSE":
                    turns.append(f"Assistant: {content}")
    except Exception:
        return
        
    if not turns:
        return
        
    # Take the last 6 turns (3 exchanges)
    recent_history = "\n\n".join(turns[-6:])
    
    # Write to .agy_progress.md in the current directory
    progress_file = ".agy_progress.md"
    try:
        with open(progress_file, "w", encoding="utf-8") as f:
            f.write(recent_history)
    except Exception:
        pass
