import os
import re
from datetime import datetime, timedelta
from utils import (
    GEMINI_MODELS, CLAUDE_MODELS, LOG_DIR, JSON_FILE,
    parse_log_timestamp, parse_duration, get_username,
    account_display_name, account_key
)

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
                line_lower = line.lower()
                if (
                    "resource_exhausted" in line_lower
                    or "quota exceeded" in line_lower
                    or "429" in line_lower
                    or "individual quota reached" in line_lower
                    or "too many tokens" in line_lower
                    or "rate limit" in line_lower
                ):
                    m = re.search(r"resets in ([0-9hms]+)", line, re.IGNORECASE)
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
