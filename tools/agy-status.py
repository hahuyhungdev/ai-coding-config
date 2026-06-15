#!/usr/bin/env python3
import os
import json
import subprocess
import re
import sys
import signal
from datetime import datetime, timedelta

AGY_DIR = os.path.expanduser("~/.gemini/antigravity-cli")
JSON_FILE = os.path.join(AGY_DIR, "accounts.json")
TOKEN_FILE = os.path.join(AGY_DIR, "antigravity-oauth-token")
LOG_DIR = os.path.join(AGY_DIR, "log")
REAL_AGY = "/home/huyhung/.local/bin/agy-bin"
GEMINI_FALLBACK_MODEL = "Gemini 3.5 Flash (High)"
CLAUDE_FALLBACK_MODEL = "Claude Opus 4.6 (Thinking)"
GEMINI_MODELS = [
    "Gemini 3.5 Flash (High)",
    "Gemini 3.5 Flash (Medium)",
    "Gemini 3.5 Flash (Low)",
    "Gemini 3.1 Pro (High)",
    "Gemini 3.1 Pro (Low)",
]
CLAUDE_MODELS = [
    "Claude Opus 4.6 (Thinking)",
    "Claude Sonnet 4.6 (Thinking)",
]

def parse_duration(duration_str):
    hours = 0
    minutes = 0
    seconds = 0
    m_h = re.search(r"(\d+)h", duration_str)
    m_m = re.search(r"(\d+)m", duration_str)
    m_s = re.search(r"(\d+)s", duration_str)
    if m_h:
        hours = int(m_h.group(1))
    if m_m:
        minutes = int(m_m.group(1))
    if m_s:
        seconds = int(m_s.group(1))
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)

def parse_log_timestamp(line):
    m = re.match(r"^[IWEF](\d{2})(\d{2})\s+(\d{2}):(\d{2}):(\d{2})", line)
    if m:
        month = int(m.group(1))
        day = int(m.group(2))
        hour = int(m.group(3))
        minute = int(m.group(4))
        second = int(m.group(5))
        now = datetime.now()
        try:
            dt = datetime(now.year, month, day, hour, minute, second)
            return dt
        except ValueError:
            return None
    return None

def get_username(email_or_name):
    if not email_or_name:
        return ""
    return email_or_name.split("@")[0].strip()


def get_model_pct(model_quotas, model_name, default=100):
    quota = model_quotas.get(model_name, {})
    try:
        return int(quota.get("pct", default))
    except (TypeError, ValueError):
        return default


def has_model_quota(acc, model_name, threshold=10):
    return get_model_pct(acc.get("model_quotas", {}), model_name) > threshold


def model_group_exhausted(model_quotas, model_names, threshold=10):
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

def get_log_email(log_path, accounts):
    try:
        with open(log_path, "r", errors="ignore") as lf:
            for _ in range(150):
                line = lf.readline()
                if not line:
                    break
                if "applyAuthResult" in line and "email=" in line:
                    for acc in accounts:
                        acc_email = acc.get("email") or acc.get("name")
                        if acc_email:
                            acc_user = get_username(acc_email)
                            if f"email={acc_user}" in line or acc_user in line:
                                return acc_email
    except:
        pass
    return None

def get_remaining_reset_from_logs(email, accounts):
    now = datetime.now()
    limit_time = now - timedelta(hours=5)

    log_files = []
    if os.path.exists(LOG_DIR):
        for f in os.listdir(LOG_DIR):
            if f.startswith("cli-") and f.endswith(".log"):
                path = os.path.join(LOG_DIR, f)
                log_files.append((path, os.path.getmtime(path)))
    log_files.sort(key=lambda x: x[1], reverse=True)

    target_user = get_username(email)

    for log_path, mtime in log_files:
        if datetime.fromtimestamp(mtime) < limit_time:
            continue
        log_email = get_log_email(log_path, accounts)
        if not log_email or get_username(log_email) != target_user:
            continue

        try:
            with open(log_path, "r", errors="ignore") as lf:
                lines = lf.readlines()
            for line in reversed(lines):
                if "RESOURCE_EXHAUSTED" in line or "Quota exceeded" in line or "429" in line:
                    m = re.search(r"Resets in ([0-9hms]+)", line)
                    if m:
                        duration_str = m.group(1)
                        log_dt = parse_log_timestamp(line)
                        if log_dt:
                            duration = parse_duration(duration_str)
                            blocked_until = log_dt + duration
                            if blocked_until > now:
                                remaining = blocked_until - now
                                tot_sec = int(remaining.total_seconds())
                                h = tot_sec // 3600
                                m = (tot_sec % 3600) // 60
                                s = tot_sec % 60
                                if h > 0:
                                    return f"In {h}h {m}m"
                                else:
                                    return f"In {m}m {s}s"
        except:
            pass
    return ""

def display_len(s):
    double_width_chars = sum(1 for c in s if c in "🟢🔴🟡🟠⭐")
    return len(s) + double_width_chars

def ljust_display(s, width):
    d_len = display_len(s)
    pad = max(0, width - d_len)
    return s + (" " * pad)


def format_cached_model_usage(acc, model_name):
    model_quotas = acc.get("model_quotas") or {}
    if model_name not in model_quotas:
        return "?"

    pct = get_model_pct(model_quotas, model_name, default=None)
    if pct is None:
        return "?"
    return f"{pct}%"


def account_display_name(acc, idx):
    return acc.get("email") or acc.get("name") or f"Account {idx + 1}"


def account_key(name):
    return get_username(name).lower()


def parse_log_account(line):
    m = re.search(r"applyAuthResult:?\s+email=([^,\s]+)", line)
    if m:
        return m.group(1)
    return ""


def parse_log_model(line):
    m = re.search(r'label="([^"]+)"', line)
    if m:
        return m.group(1)
    return ""


def get_weekly_usage(days=7, now=None):
    now = now or datetime.now()
    since = now - timedelta(days=days)

    accounts = []
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r") as f:
                accounts = json.load(f)
        except Exception:
            accounts = []

    usage = {}
    for idx, acc in enumerate(accounts):
        name = account_display_name(acc, idx)
        usage[account_key(name)] = {
            "account": name,
            "sessions": 0,
            "prompts": 0,
            "gemini_prompts": 0,
            "opus_prompts": 0,
            "quota_errors": 0,
        }

    if not os.path.exists(LOG_DIR):
        return list(usage.values())

    for fname in os.listdir(LOG_DIR):
        if not fname.startswith("cli-") or not fname.endswith(".log"):
            continue
        path = os.path.join(LOG_DIR, fname)
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
        except OSError:
            continue
        if mtime < since:
            continue

        email = ""
        model = ""
        prompts = 0
        quota_error_seen = False
        try:
            with open(path, "r", errors="ignore") as lf:
                for line in lf:
                    parsed_email = parse_log_account(line)
                    if parsed_email:
                        email = parsed_email
                    parsed_model = parse_log_model(line)
                    if parsed_model:
                        model = parsed_model
                    if "HandleUserInput called with text:" in line:
                        prompts += 1
                    if (
                        "RESOURCE_EXHAUSTED" in line
                        or "Quota exceeded" in line
                        or "Individual quota reached" in line
                        or "Too many tokens" in line
                        or "Rate limit" in line
                    ):
                        quota_error_seen = True
        except OSError:
            continue

        if not email:
            continue

        key = account_key(email)
        if key not in usage:
            usage[key] = {
                "account": email,
                "sessions": 0,
                "prompts": 0,
                "gemini_prompts": 0,
                "opus_prompts": 0,
                "quota_errors": 0,
            }

        row = usage[key]
        row["sessions"] += 1
        row["prompts"] += prompts
        if quota_error_seen:
            row["quota_errors"] += 1
        if "gemini" in model.lower():
            row["gemini_prompts"] += prompts
        elif "opus" in model.lower():
            row["opus_prompts"] += prompts

    return sorted(usage.values(), key=lambda r: (r["prompts"], r["sessions"]), reverse=True)


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


def strip_ansi(text):
    return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)


def get_quota_via_pty(email):
    import pty
    import os
    import time
    import fcntl
    import termios
    import struct
    import select
    
    master, slave = pty.openpty()
    s = struct.pack("HHHH", 24, 80, 0, 0)
    try:
        fcntl.ioctl(master, termios.TIOCSWINSZ, s)
    except:
        pass
        
    pid = os.fork()
    if pid == 0:
        os.setsid()
        os.dup2(slave, 0)
        os.dup2(slave, 1)
        os.dup2(slave, 2)
        os.close(master)
        os.close(slave)
        try:
            os.execv(REAL_AGY, [REAL_AGY])
        except:
            os._exit(127)
    else:
        os.close(slave)
        
        output = b""
        
        # Wait dynamically for prompt (e.g. '>') or 'shortcuts' up to 12 seconds
        start_time = time.time()
        while time.time() - start_time < 12.0:
            r, _, _ = select.select([master], [], [], 0.1)
            if r:
                try:
                    chunk = os.read(master, 4096)
                    if not chunk:
                        break
                    output += chunk
                    if b"\r\n>" in output or b"shortcuts" in output:
                        # Flush any remaining bytes
                        time.sleep(0.1)
                        r2, _, _ = select.select([master], [], [], 0.05)
                        if r2:
                            output += os.read(master, 4096)
                        break
                except OSError:
                    break
            else:
                time.sleep(0.05)
        
        # Send /usage
        try:
            os.write(master, b"/usage\x0d")
        except:
            pass
            
        # Read quota output (up to 4 seconds)
        quota_start = time.time()
        while time.time() - quota_start < 4:
            r, _, _ = select.select([master], [], [], 0.2)
            if r:
                try:
                    chunk = os.read(master, 4096)
                    if not chunk:
                        break
                    output += chunk
                    if b"Model Quota" in chunk or b"remaining" in chunk or b"Quota available" in chunk or b"matches" in chunk:
                        time.sleep(0.3)
                        r2, _, _ = select.select([master], [], [], 0.05)
                        if r2:
                            output += os.read(master, 4096)
                        break
                except OSError:
                    break
                    
        # Send exit command
        try:
            os.write(master, b"/exit\x0d")
        except:
            pass
            
        # The CLI may ignore /exit while it is still rendering. Never return
        # while it can still rewrite the shared token file.
        try:
            deadline = time.time() + 2.0
            while time.time() < deadline:
                finished, _ = os.waitpid(pid, os.WNOHANG)
                if finished == pid:
                    break
                time.sleep(0.1)
            else:
                os.killpg(pid, signal.SIGTERM)
                deadline = time.time() + 1.0
                while time.time() < deadline:
                    finished, _ = os.waitpid(pid, os.WNOHANG)
                    if finished == pid:
                        break
                    time.sleep(0.1)
                else:
                    os.killpg(pid, signal.SIGKILL)
                    os.waitpid(pid, 0)
        except (ChildProcessError, ProcessLookupError):
            pass
        finally:
            os.close(master)
            
        return strip_ansi(output.decode(errors="ignore"))

def parse_quota_output(output):
    # Try new group-based parser first
    group_quotas = {
        "GEMINI": {"weekly": {"pct": 100, "refresh": ""}, "five_hour": {"pct": 100, "refresh": ""}},
        "CLAUDE": {"weekly": {"pct": 100, "refresh": ""}, "five_hour": {"pct": 100, "refresh": ""}}
    }
    found_new_format = False
    current_group = None
    current_limit = None
    
    def get_group_quota(group_data):
        w = group_data["weekly"]
        f = group_data["five_hour"]
        if w["pct"] < f["pct"]:
            return w["pct"], w["refresh"]
        elif f["pct"] < w["pct"]:
            return f["pct"], f["refresh"]
        else:
            refresh = f["refresh"] or w["refresh"]
            return w["pct"], refresh

    lines = output.splitlines()
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue
        if "GEMINI MODELS" in line:
            current_group = "GEMINI"
            current_limit = None
            found_new_format = True
            continue
        elif "CLAUDE AND GPT MODELS" in line:
            current_group = "CLAUDE"
            current_limit = None
            found_new_format = True
            continue
            
        if current_group:
            if "Weekly Limit" in line:
                current_limit = "weekly"
                continue
            elif "Five Hour Limit" in line or "5-Hour Limit" in line:
                current_limit = "five_hour"
                continue
                
            if current_limit:
                if "remaining" in line_strip or "Refreshes in" in line_strip:
                    m_ref = re.search(r"Refreshes in\s*(.*)", line_strip)
                    if m_ref:
                        group_quotas[current_group][current_limit]["refresh"] = "In " + m_ref.group(1).split("·")[0].strip()
                    current_limit = None
                    continue
                elif "Quota available" in line_strip:
                    group_quotas[current_group][current_limit]["refresh"] = ""
                    current_limit = None
                    continue
                
                m_pct = re.search(r"(\d+(?:\.\d+)?)%", line_strip)
                if m_pct:
                    pct_val = float(m_pct.group(1))
                    group_quotas[current_group][current_limit]["pct"] = int(round(pct_val))
                    continue

    model_quotas = {}
    if found_new_format:
        gemini_pct, gemini_ref = get_group_quota(group_quotas["GEMINI"])
        claude_pct, claude_ref = get_group_quota(group_quotas["CLAUDE"])
        
        for model in GEMINI_MODELS:
            model_quotas[model] = {
                "pct": gemini_pct, 
                "refresh": gemini_ref,
                "weekly_pct": group_quotas["GEMINI"]["weekly"]["pct"],
                "weekly_refresh": group_quotas["GEMINI"]["weekly"]["refresh"],
                "five_hour_pct": group_quotas["GEMINI"]["five_hour"]["pct"],
                "five_hour_refresh": group_quotas["GEMINI"]["five_hour"]["refresh"]
            }
        for model in CLAUDE_MODELS + ["GPT-OSS 120B (Medium)"]:
            model_quotas[model] = {
                "pct": claude_pct, 
                "refresh": claude_ref,
                "weekly_pct": group_quotas["CLAUDE"]["weekly"]["pct"],
                "weekly_refresh": group_quotas["CLAUDE"]["weekly"]["refresh"],
                "five_hour_pct": group_quotas["CLAUDE"]["five_hour"]["pct"],
                "five_hour_refresh": group_quotas["CLAUDE"]["five_hour"]["refresh"]
            }
    else:
        # Fall back to old line-by-line parser
        i = 0
        while i < len(lines):
            line = lines[i]
            model_name = None
            for known in GEMINI_MODELS + CLAUDE_MODELS + ["GPT-OSS 120B (Medium)"]:
                if known in line:
                    model_name = known
                    break

            if model_name:
                pct = 100
                refresh = ""
                for j in range(i+1, min(i+5, len(lines))):
                    next_line = lines[j]
                    if any(known in next_line for known in GEMINI_MODELS + CLAUDE_MODELS + ["GPT-OSS 120B (Medium)"]):
                        break
                    m_pct = re.search(r"(\d+)%", next_line)
                    if m_pct:
                        pct = int(m_pct.group(1))
                    m_ref = re.search(r"Refreshes in\s*(.*)", next_line)
                    if m_ref:
                        refresh = "In " + m_ref.group(1).split("·")[0].strip()
                model_quotas[model_name] = {
                    "pct": pct, 
                    "refresh": refresh,
                    "weekly_pct": pct,
                    "weekly_refresh": refresh,
                    "five_hour_pct": pct,
                    "five_hour_refresh": refresh
                }
            i += 1
            
    return model_quotas

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

    status_report = []
    duplicate_tokens = find_duplicate_refresh_tokens(accounts)

    try:
        for idx, acc in enumerate(accounts):
            email = acc.get("email") or acc.get("name") or f"Account {idx}"

            if idx in duplicate_tokens:
                original_idx = duplicate_tokens[idx]
                status_report.append({
                    "index": idx,
                    "email": email,
                    "status": "🟡 Dup",
                    "quota": f"Same as #{original_idx + 1}",
                    "reset_info": ""
                })
                continue
            
            # Print in-place progress update
            print(f"⏳ [{idx+1}/{len(accounts)}] Checking status for {email}...", end="\r", flush=True)
            
            test_dir = os.path.join(AGY_DIR, f"scratch/test_dir_{idx}")
            os.makedirs(test_dir, exist_ok=True)

            # Temporarily write this account token
            with open(TOKEN_FILE, "w") as f:
                json.dump(acc, f)

            # Run interactive PTY to fetch the real quota
            output = get_quota_via_pty(email)

            # Read refreshed token JSON and update accounts list
            try:
                with open(TOKEN_FILE, "r") as f:
                    refreshed_acc = json.load(f)
                    accounts[idx]["token"] = refreshed_acc["token"]
            except Exception:
                pass

            status = "🔴 Blocked"
            reset_time_str = ""
            quota_str = "0%"

            if "Model Quota" in output or "Model Usage" in output or "Quota" in output or "GEMINI MODELS" in output or "CLAUDE AND GPT MODELS" in output:
                status = "🟢 Ready"
                quota_str = "100%"

                model_quotas = parse_quota_output(output)

                # Determine overall status from model_quotas
                # Use the first Gemini model for the summary display
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
                                if w_ref and f_ref:
                                    w_clean = w_ref.replace("In ", "").strip()
                                    f_clean = f_ref.replace("In ", "").strip()
                                    reset_time_str = f"5H:{f_clean}/W:{w_clean}"
                                elif f_ref:
                                    reset_time_str = f"5H:{f_ref.replace('In ', '')}"
                                elif w_ref:
                                    reset_time_str = f"W:{w_ref.replace('In ', '')}"
                                else:
                                    reset_time_str = ""
                            else:
                                quota_str = f"{q['pct']}%"
                                if q['refresh']:
                                    reset_time_str = q['refresh']
                            break

                    # Check if ALL models are at 0%
                    all_zero = all(m["pct"] == 0 for m in model_quotas.values())
                    if all_zero:
                        status = "🔴 Blocked"
                        quota_str = "0%"
            else:
                # If we could not fetch quota, check if it was due to being completely blocked
                reset_time_str = get_remaining_reset_from_logs(email, accounts)
                if reset_time_str:
                    status = "🔴 Blocked"
                    quota_str = "🔴 0% (Blocked)"
                else:
                    # Assume it was ready but timed out / didn't show menu
                    status = "🟢 Ready"
                    quota_str = "100%" 

            # Cache the status and quota check results
            accounts[idx]["status"] = status
            accounts[idx]["quota"] = quota_str
            accounts[idx]["reset_info"] = reset_time_str
            accounts[idx]["last_checked"] = datetime.now().isoformat()
            # Store per-model quota for smart model selection
            if 'model_quotas' in dir() and model_quotas:
                accounts[idx]["model_quotas"] = model_quotas

            is_active_label = " ⭐" if active_email and get_username(email) == get_username(active_email) else ""
            status_report.append({
                "index": idx,
                "email": email + is_active_label,
                "status": status,
                "quota": quota_str,
                "reset_info": reset_time_str
            })

        # Save refreshed tokens back to accounts.json
        with open(JSON_FILE, "w") as f:
            json.dump(accounts, f, indent=2)

    finally:
        # Restore original active token
        if orig_token is not None:
            with open(TOKEN_FILE, "w") as f:
                f.write(orig_token)

    # Clear progress line
    print(" " * 80, end="\r", flush=True)

    # Display narrow table
    print("┌────┬──────────────────────┬──────────┬──────────────────┬────────────────────────┐")
    print("│IDX │ ACCOUNT              │ STATUS   │ QUOTA            │ RESET TIME             │")
    print("├────┼──────────────────────┼──────────┼──────────────────┼────────────────────────┤")
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
        reset_str_padded = ljust_display(row['reset_info'], 22)

        print(f"│{idx_str}│ {email_str_padded} │ {status_str_padded} │ {quota_str_padded} │ {reset_str_padded} │")
    print("└────┴──────────────────────┴──────────┴──────────────────┴────────────────────────┘")
    print("(* Quota shows account readiness. ⭐ indicates active account.)")

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

    print("┌─────┬──────────────────────┬──────────┬────────┬────────┐")
    print("│ IDX │ ACCOUNT              │ ACTIVE   │ GEMINI │ OPUS   │")
    print("├─────┼──────────────────────┼──────────┼────────┼────────┤")
    for idx, acc in enumerate(accounts):
        name = acc.get("email") or acc.get("name") or f"Account {idx}"
        idx_str = f"{idx + 1}".center(5)
        name_padded = ljust_display(name, 20)
        is_active = "⭐" if active_email and get_username(name) == get_username(active_email) else ""
        active_padded = ljust_display(is_active, 8)
        gemini_usage = format_cached_model_usage(acc, GEMINI_FALLBACK_MODEL)
        opus_usage = format_cached_model_usage(acc, CLAUDE_FALLBACK_MODEL)
        gemini_padded = ljust_display(gemini_usage, 6)
        opus_padded = ljust_display(opus_usage, 6)
        print(f"│{idx_str}│ {name_padded} │ {active_padded} │ {gemini_padded} │ {opus_padded} │")
    print("└─────┴──────────────────────┴──────────┴────────┴────────┘")
    print("Gemini = Gemini 3.5 Flash (High); Opus = Claude Opus 4.6 (Thinking). '?' means run 'agy status' to refresh.")


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
        print("To remove, run: agyswap remove-account <idx> or agyswap remove-account <email_or_name>")
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

    removed_acc = accounts.pop(matched_idx)
    removed_name = removed_acc.get("email") or removed_acc.get("name") or f"Account {matched_idx}"

    with open(JSON_FILE, "w") as f:
        json.dump(accounts, f, indent=2)

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
                            import re
                            m = re.search(r"email=([^,\s]+)", line)
                            if m:
                                email = m.group(1)
                                break
            except:
                pass
                
    if not email:
        print("❌ Could not auto-detect email. Please specify your account name:")
        print("   agyswap add-current <email_or_name>")
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
            updated = True
            break

    if not updated:
        accounts.append({
            "email": username,
            "auth_method": current_data.get("auth_method", "consumer"),
            "token": current_data.get("token") or current_data
        })
        print(f"🟢 Successfully added new account '{username}' to accounts.json!")
    else:
        print(f"🟢 Successfully updated existing account '{username}' in accounts.json!")

    with open(JSON_FILE, "w") as f:
        json.dump(accounts, f, indent=2)


def clean_conversations():
    import shutil
    
    # 1. Read history.jsonl to find active conversation IDs
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

    # 2. Scan conversations/ directory for .db and .pb files
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
    import shutil
    
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
        print("To delete, run: agyswap delete <idx> or agyswap delete <conversation_id>")
        return

    selected_cid = None
    if target.isdigit():
        idx = int(target) - 1  # User-facing indexes are 1-based
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

    # Perform deletion of files
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

    # Support both raw token object and wrapped format {"token": {...}}
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
            email = "account-" + str(len(accounts) if 'accounts' in dir() else "")
            print(f"⏳ Using default label: '{email}'")

    username = get_username(email)

    accounts = []
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r") as f:
                accounts = json.load(f)
        except Exception:
            pass

    # Check if account already exists
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

    with open(JSON_FILE, "w") as f:
        json.dump(accounts, f, indent=2)

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

    # Support both raw token object and wrapped format {"token": {...}}
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
        # Try to extract from access_token JWT or use filename
        basename = os.path.splitext(os.path.basename(file_path))[0]
        email = basename
        print(f"⏳ No email specified, using filename as label: '{email}'")

    username = get_username(email)

    accounts = []
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r") as f:
                accounts = json.load(f)
        except Exception:
            pass

    # Check if account already exists
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

    with open(JSON_FILE, "w") as f:
        json.dump(accounts, f, indent=2)

    print(f"   Total accounts: {len(accounts)}")



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
        # Check if the block has expired (if we know the reset time and when it was checked)
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
        m = re.search(r"(\d+)%", quota_val)
        if m:
            pct = int(m.group(1))
            if pct <= 10:  # Switch when quota is running low (<= 10%)
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

    # Find the most recent log file
    log_files = []
    for f in os.listdir(LOG_DIR):
        if f.startswith("cli-") and f.endswith(".log"):
            path = os.path.join(LOG_DIR, f)
            log_files.append((path, os.path.getmtime(path)))
    if not log_files:
        return False, "", ""

    log_files.sort(key=lambda x: x[1], reverse=True)
    latest_log = log_files[0][0]

    # Only check logs modified in the last 2 minutes (recent session)
    from datetime import datetime, timedelta
    if datetime.fromtimestamp(log_files[0][1]) < datetime.now() - timedelta(minutes=2):
        return False, "", ""

    try:
        with open(latest_log, "r", errors="ignore") as f:
            lines = f.readlines()

        # Step 1: Find which model was being used (look for model label before error)
        blocked_model = "unknown"
        for line in reversed(lines[-80:]):
            m = re.search(r'Propagating selected model override.*label="(.*?)"', line)
            if m:
                label = m.group(1).lower()
                if "claude" in label:
                    blocked_model = "claude"
                elif "gemini" in label:
                    blocked_model = "gemini"
                break

        # Step 2: Scan last 50 lines for quota error (it appears near the end)
        for line in reversed(lines[-50:]):
            if "RESOURCE_EXHAUSTED" in line or "Quota exceeded" in line:
                # Extract reset time
                m = re.search(r"Resets in\s*([0-9hms]+)", line)
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
        # No active account, switch to index 0
        active_idx = 0
        selected_acc = accounts[0]
        with open(TOKEN_FILE, "w") as f:
            json.dump(selected_acc, f)
        email = selected_acc.get("email") or selected_acc.get("name") or "Account 1"
        if not quiet:
            print(f"🔄 Initialized active account to: {email}")
        return ""

    active_acc = accounts[active_idx]
    active_email = active_acc.get("email") or active_acc.get("name") or f"Account {active_idx + 1}"

    # Check if current active account is blocked or has low quota
    if is_account_blocked_or_low(active_acc, accounts):
        if not quiet:
            print(f"⚠️ Current account '{active_email}' is blocked or has low quota (<=10%). Searching for replacement...")

        # Detect which model was blocked (from recent logs)
        _, _, blocked_model = check_last_log_for_quota_error()
        # Fallback: check cached data
        if not blocked_model or blocked_model == "unknown":
            blocked_model = active_acc.get("last_blocked_model", "")

        suggestion = get_model_suggestion(active_acc, blocked_model=blocked_model)
        if suggestion:
            print(f"MODEL:{suggestion}")
            return suggestion

        # Search circularly for a good account starting from the next index
        found_idx = None
        for i in range(1, len(accounts)):
            candidate_idx = (active_idx + i) % len(accounts)
            candidate_acc = accounts[candidate_idx]
            if not is_account_blocked_or_low(candidate_acc, accounts):
                found_idx = candidate_idx
                break

        if found_idx is not None:
            # Switch to this account!
            selected_acc = accounts[found_idx]
            with open(TOKEN_FILE, "w") as f:
                json.dump(selected_acc, f)

            # Update current index file
            INDEX_FILE = os.path.join(AGY_DIR, ".current_index")
            with open(INDEX_FILE, "w") as f:
                f.write(str((found_idx + 1) % len(accounts)))

            new_email = selected_acc.get("email") or selected_acc.get("name")
            print(f"🔄 Auto-switched account to: {new_email} (Index: [{found_idx + 1}])")

            suggestion = get_model_suggestion(selected_acc, blocked_model=blocked_model)
            if suggestion:
                print(f"MODEL:{suggestion}")
                return suggestion
        else:
            if not quiet:
                print("⚠️ All accounts are currently blocked or low on quota! Staying on the current account.")
    else:
        # Current account is good overall, but check if the last session hit a quota error
        # This catches per-model blocks that the overall account status misses
        had_error, _, blocked_model = check_last_log_for_quota_error()
        if had_error and blocked_model and blocked_model != "unknown":
            suggestion = get_model_suggestion(active_acc, blocked_model=blocked_model)
            if suggestion:
                print(f"MODEL:{suggestion}")
                return suggestion

        # Also check cached model_quotas (populated by agy status)
        model_quotas = active_acc.get("model_quotas", {})
        if model_quotas:
            suggestion = get_model_suggestion(active_acc)
            if suggestion:
                print(f"MODEL:{suggestion}")
                return suggestion

    return ""


def post_check_and_switch():
    """Called AFTER agy-bin exits. Checks if the session failed due to quota,
    then tries the other model on the same account, or switches account.

    Exit codes:
      0 = switched (model or account) — caller should retry
      1 = no quota error detected (normal exit, no retry needed)
      2 = quota error found but ALL accounts are blocked (no switch possible)

    Prints a suggestion line for the wrapper to parse:
      SWITCH_MODEL:<model_label>   — retry same account with different model
      SWITCH_ACCOUNT               — retry with different account
    """
    # Step 1: Check if the last session hit a quota error
    had_quota_error, reset_time, blocked_model = check_last_log_for_quota_error()
    if not had_quota_error:
        sys.exit(1)  # No quota error, no retry needed

    print(f"⚠️ Quota exhausted on {blocked_model} model! {reset_time}")

    # Step 2: Try the OTHER model on the same account first
    if blocked_model == "gemini":
        fallback_model = CLAUDE_FALLBACK_MODEL
        fallback_label = "claude"
    else:
        fallback_model = None
        fallback_label = None

    if fallback_model:
        print(f"🔄 Trying {fallback_label} model on same account...")
        print(f"SWITCH_MODEL:{fallback_model}")
        sys.exit(0)  # Caller should retry with --model flag

    # Step 3: If model unknown, fall through to account switching
    # Mark current account as blocked
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
            accounts[active_idx]["reset_info"] = reset_time
        accounts[active_idx]["last_checked"] = datetime.now().isoformat()
        with open(JSON_FILE, "w") as f:
            json.dump(accounts, f, indent=2)

    if active_idx is None:
        active_idx = 0

    found_idx = None
    for i in range(1, len(accounts)):
        candidate_idx = (active_idx + i) % len(accounts)
        candidate_acc = accounts[candidate_idx]
        if not is_account_blocked_or_low(candidate_acc, accounts):
            found_idx = candidate_idx
            break

    if found_idx is not None:
        selected_acc = accounts[found_idx]
        with open(TOKEN_FILE, "w") as f:
            json.dump(selected_acc, f)

        INDEX_FILE = os.path.join(AGY_DIR, ".current_index")
        with open(INDEX_FILE, "w") as f:
            f.write(str((found_idx + 1) % len(accounts)))

        new_email = selected_acc.get("email") or selected_acc.get("name")
        print(f"🔄 Switched to: {new_email} (Index: [{found_idx + 1}]) — retrying...")
        print("SWITCH_ACCOUNT")
        sys.exit(0)
    else:
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
        next_idx = 0
    else:
        next_idx = (active_idx + 1) % len(accounts)

    selected_acc = accounts[next_idx]
    with open(TOKEN_FILE, "w") as f:
        json.dump(selected_acc, f)

    INDEX_FILE = os.path.join(AGY_DIR, ".current_index")
    with open(INDEX_FILE, "w") as f:
        f.write(str((next_idx + 1) % len(accounts)))

    email = selected_acc.get("email") or selected_acc.get("name") or f"Account {next_idx + 1}"
    print(f"🔄 Manually rotated active account to: {email} (Index: [{next_idx + 1} / {len(accounts)}])")


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
