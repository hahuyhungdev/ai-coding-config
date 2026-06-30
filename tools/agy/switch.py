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
    get_model_pct, format_exact_reset_time, remaining_quota_value,
    clear_mcp_token_cache
)
from parser import get_remaining_reset_from_logs

SETTINGS_FILE = os.path.join(AGY_DIR, "settings.json")
ROUND_ROBIN_POLICY = "round-robin"
HIGHEST_QUOTA_POLICY = "highest-quota"


def _sync_paths():
    import storage, parser
    storage.JSON_FILE = JSON_FILE
    storage.TOKEN_FILE = TOKEN_FILE
    storage.AGY_DIR = AGY_DIR
    parser.JSON_FILE = JSON_FILE
    parser.LOG_DIR = LOG_DIR


def load_rotation_policy():
    _sync_paths()
    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
    except Exception:
        return HIGHEST_QUOTA_POLICY

    raw_policy = (
        settings.get("rotationPolicy")
        or settings.get("rotation_policy")
        or HIGHEST_QUOTA_POLICY
    )
    policy = str(raw_policy).strip().lower().replace("_", "-")
    # Since round-robin is removed, always fall back or return highest-quota
    return HIGHEST_QUOTA_POLICY


def load_quota_threshold():
    _sync_paths()
    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
    except Exception:
        return 15

    raw_threshold = (
        settings.get("quotaThreshold")
        or settings.get("quota_threshold")
        or settings.get("threshold")
        or 15
    )
    try:
        return int(raw_threshold)
    except (ValueError, TypeError):
        return 15


def load_quota_thresholds():
    _sync_paths()
    settings = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
        except Exception:
            pass

    raw_5h = (
        settings.get("threshold_5h")
        or settings.get("threshold5h")
        or settings.get("threshold")
        or settings.get("quotaThreshold")
        or settings.get("quota_threshold")
        or 15
    )
    
    raw_weekly = (
        settings.get("threshold_weekly")
        or settings.get("thresholdWeekly")
        or settings.get("threshold_weekly_limit")
        or 10
    )
    
    try:
        t_5h = int(raw_5h)
    except (ValueError, TypeError):
        t_5h = 15
        
    try:
        t_weekly = int(raw_weekly)
    except (ValueError, TypeError):
        t_weekly = 10
        
    return t_5h, t_weekly



def _candidate_indexes(accounts, active_idx):
    if len(accounts) <= 1:
        return []
    return [(active_idx + offset) % len(accounts) for offset in range(1, len(accounts))]


def _best_remaining_quota_index(accounts, indexes):
    best_idx = None
    best_quota = -2
    for idx in indexes:
        quota = remaining_quota_value(accounts[idx].get("quota"))
        if quota > best_quota:
            best_quota = quota
            best_idx = idx
    return best_idx


def select_replacement_index(accounts, active_idx, policy=None, allow_best_effort=True):
    _sync_paths()
    policy = policy or load_rotation_policy()
    indexes = _candidate_indexes(accounts, active_idx)
    if not indexes:
        return None

    from status_refresh import find_duplicate_refresh_tokens
    duplicates = find_duplicate_refresh_tokens(accounts)
    indexes = [idx for idx in indexes if idx not in duplicates]
    if not indexes:
        return None

    healthy_indexes = [
        idx for idx in indexes
        if not is_account_blocked_or_low(accounts[idx], accounts)
    ]

    if healthy_indexes:
        return _best_remaining_quota_index(accounts, healthy_indexes)

    if allow_best_effort:
        low_quota_indexes = [
            idx for idx in indexes
            if accounts[idx].get("status") != "🔴 Blocked"
        ]
        return _best_remaining_quota_index(accounts, low_quota_indexes)
    return None


def _write_active_account(accounts, selected_idx):
    _sync_paths()
    from storage import sync_active_token_to_accounts
    try:
        sync_active_token_to_accounts()
    except Exception:
        pass
    selected_acc = accounts[selected_idx]
    with open(TOKEN_FILE, "w") as f:
        json.dump(selected_acc, f)
    if os.name == 'posix':
        try:
            os.chmod(TOKEN_FILE, 0o600)
        except OSError:
            pass

    clear_mcp_token_cache()

    index_file = os.path.join(AGY_DIR, ".current_index")
    with open(index_file, "w") as f:
        f.write(str((selected_idx + 1) % len(accounts)))

    return selected_acc


def has_model_quota(acc, model_name, threshold=None):
    if threshold is None:
        threshold = load_quota_threshold()
    return get_model_pct(acc.get("model_quotas", {}), model_name) > threshold

def model_group_exhausted(model_quotas, model_names, threshold=None):
    if threshold is None:
        threshold = load_quota_threshold()
    present = [name for name in model_names if name in model_quotas]
    return bool(present) and all(get_model_pct(model_quotas, name) <= threshold for name in present)

def choose_same_account_fallback(acc, blocked_model=""):
    """Prefer Gemini first; never fall back to Claude Opus."""
    # Never fall back from Claude or GPT to Gemini
    if blocked_model in ("claude", "gpt"):
        return ""

    model_quotas = acc.get("model_quotas", {})

    if model_quotas:
        # If Gemini is blocked or unavailable, do not fall back to Claude Opus
        if blocked_model == "gemini":
            return ""

        # No blocked model: prefer Gemini first
        if has_model_quota(acc, GEMINI_FALLBACK_MODEL):
            return GEMINI_FALLBACK_MODEL

    return ""

def is_account_blocked_or_low(acc, accounts):
    _sync_paths()
    email = acc.get("email") or acc.get("name")
    if not email:
        return True
    
    # 1. Check cached quota percentage first (proactive check before expensive log scan)
    quota_val = acc.get("quota")
    if quota_val:
        from utils import parse_quota_percentages
        pct_5h, pct_w = parse_quota_percentages(quota_val)
        t_5h, t_w = load_quota_thresholds()
        if (pct_5h != -1 and pct_5h <= t_5h) or (pct_w != -1 and pct_w <= t_w):
            return True
        
    # 2. Real-time log check (most accurate for active blocks)
    reset_time = get_remaining_reset_from_logs(email, accounts)
    if reset_time:
        return True
        
    # 3. Check cached status
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
            if last_checked_str:
                try:
                    last_checked = datetime.fromisoformat(last_checked_str)
                    if datetime.now() >= last_checked + timedelta(hours=2):
                        return False
                except:
                    pass
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
                elif "gpt" in label:
                    blocked_model = "gpt"
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
    _sync_paths()
    from storage import load_accounts
    try:
        accounts = load_accounts()
    except Exception as e:
        if not quiet:
            print(f"❌ Failed to load accounts: {e}")
        return ""

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
            t_5h, t_w = load_quota_thresholds()
            print(f"⚠️ Current account '{active_email}' is blocked or has low quota (5H<={t_5h}%, W<={t_w}%). Searching for replacement...")

        policy = load_rotation_policy()
        found_idx = select_replacement_index(accounts, active_idx, policy=policy)

        if found_idx is not None:
            selected_acc = _write_active_account(accounts, found_idx)
            new_email = selected_acc.get("email") or selected_acc.get("name")
            quota = selected_acc.get("quota", "?")
            reset_info = selected_acc.get("reset_info", "")
            quota_str = f" - Quota: {quota}"
            if reset_info:
                quota_str += f" ({reset_info})"
            if not quiet:
                print(f"🔄 Auto-switched account to: {new_email} (Index: [{found_idx + 1}], policy: {policy}){quota_str}")

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
    _sync_paths()
    had_quota_error, reset_time, blocked_model = check_last_log_for_quota_error()
    if not had_quota_error:
        sys.exit(1)

    print(f"⚠️ Quota exhausted on {blocked_model} model! {reset_time}")

    from storage import load_accounts
    try:
        accounts = load_accounts()
    except Exception as e:
        print(f"❌ Failed to load accounts: {e}", file=sys.stderr)
        sys.exit(1)

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

    policy = load_rotation_policy()
    found_idx = select_replacement_index(accounts, active_idx, policy=policy)

    if found_idx is not None:
        selected_acc = _write_active_account(accounts, found_idx)
        new_email = selected_acc.get("email") or selected_acc.get("name")
        quota = selected_acc.get("quota", "?")
        reset_info = selected_acc.get("reset_info", "")
        quota_str = f" - Quota: {quota}"
        if reset_info:
            quota_str += f" ({reset_info})"
        generate_quota_rollover()
        print(f"🔄 Switched to: {new_email} (Index: [{found_idx + 1}], policy: {policy}){quota_str} — retrying...")
        print("SWITCH_ACCOUNT")
        sys.exit(0)
    else:
        print("❌ All accounts are blocked! Cannot retry.")
        sys.exit(2)

def kill_ancestor_agy_bin():
    import signal
    if os.environ.get("AGY_TESTING") == "1":
        return False
    pid = os.getpid()
    while pid > 1:
        try:
            with open(f"/proc/{pid}/stat", "r") as f:
                parts = f.read().split()
            ppid = int(parts[3])
            comm = parts[1].strip("()")
            
            if "agy-bin" in comm.lower():
                print(f"Found agy-bin ancestor (PID: {pid}). Terminating cleanly...", file=sys.stderr)
                os.kill(pid, signal.SIGTERM)
                return True
            pid = ppid
        except Exception:
            break
    return False

def rotate_account(target=None, force=False):
    _sync_paths()
    from storage import load_accounts
    try:
        accounts = load_accounts()
    except Exception as e:
        print(f"❌ Failed to load accounts: {e}")
        return

    if not accounts:
        print("❌ No accounts in accounts.json!")
        return

    active_idx = 0
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

    found_idx = None
    if target:
        target_str = str(target)
        if target_str.isdigit():
            idx = int(target_str) - 1
            if 0 <= idx < len(accounts):
                found_idx = idx
        else:
            for idx, acc in enumerate(accounts):
                email = acc.get("email") or acc.get("name") or ""
                if target_str.lower() in email.lower():
                    found_idx = idx
                    break
        if found_idx is None:
            print(f"❌ Error: Target '{target}' not found in accounts pool.")
            return
    else:
        if len(accounts) <= 1:
            print("ℹ️ Only one account in accounts.json. No rotation possible.")
            return

        if force:
            found_idx = (active_idx + 1) % len(accounts)
        else:
            active_acc = accounts[active_idx]
            if not is_account_blocked_or_low(active_acc, accounts):
                active_email = active_acc.get("email") or active_acc.get("name") or f"Account {active_idx + 1}"
                quota = active_acc.get("quota", "?")
                reset_info = active_acc.get("reset_info", "")
                t_5h, t_w = load_quota_thresholds()
                quota_str = f" - Quota: {quota}"
                if reset_info:
                    quota_str += f" ({reset_info})"
                print(
                    f"ℹ️ Current account '{active_email}' is healthy "
                    f"(thresholds: 5H<={t_5h}%, W<={t_w}%){quota_str}. "
                    "No rotation needed. Use 'agy rotate --force' to rotate anyway."
                )
                return

            policy = load_rotation_policy()
            found_idx = select_replacement_index(accounts, active_idx, policy=policy)
            if found_idx is None:
                print("⚠️ No replacement account is currently eligible. Staying on the current account.")
                return

    selected_acc = _write_active_account(accounts, found_idx)
    new_email = selected_acc.get("email") or selected_acc.get("name") or f"Account {found_idx + 1}"
    new_quota = selected_acc.get("quota", "?")
    reset_info = selected_acc.get("reset_info", "")
    quota_str = f" - Quota: {new_quota}"
    if reset_info:
        quota_str += f" ({reset_info})"
        
    print(f"🔄 Switched active account to: {new_email} (Index: [{found_idx + 1} / {len(accounts)}]){quota_str}")

    # Check if we are running inside an active agy-bin session
    is_inside_session = False
    curr_pid = os.getpid()
    while curr_pid > 1:
        try:
            with open(f"/proc/{curr_pid}/stat", "r") as f:
                parts = f.read().split()
            ppid = int(parts[3])
            comm = parts[1].strip("()")
            if "agy-bin" in comm.lower():
                is_inside_session = True
                break
            curr_pid = ppid
        except:
            break

    if is_inside_session and os.environ.get("AGY_TESTING") != "1":
        print("📝 Saving active conversation history...")
        generate_quota_rollover()
        
        # Touch the compaction signal file
        from pathlib import Path
        signal_file = Path(AGY_DIR) / ".compact_signal"
        try:
            signal_file.touch()
        except:
            pass
            
        kill_ancestor_agy_bin()


def generate_quota_rollover():
    _sync_paths()
    # Check if a custom structured progress summary already exists; if so, preserve it
    for progress_name in [".agy_progress.md", "PROGRESS.md"]:
        if os.path.exists(progress_name) and os.path.getsize(progress_name) > 0:
            return
            
    brain_dir = os.path.expanduser(os.path.join(AGY_DIR, "brain"))
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
        
    # Filter out turns relating to the account rotation or switch command to prevent infinite loop
    filtered_turns = []
    for turn in turns:
        turn_lower = turn.lower()
        if (
            "rotate" in turn_lower
            or "switch-account" in turn_lower
            or "switch account" in turn_lower
            or "switch_session" in turn_lower
        ):
            continue
        filtered_turns.append(turn)

    if not filtered_turns:
        filtered_turns = ["No recent history before rotation."]
        
    # Take the last 6 turns (3 exchanges)
    recent_history = "\n\n".join(filtered_turns[-6:])
    
    # Write to .agy_progress.md in the current directory
    progress_file = ".agy_progress.md"
    try:
        with open(progress_file, "w", encoding="utf-8") as f:
            f.write(recent_history)
    except Exception:
        pass
