import os
import re
from datetime import datetime, timedelta

# Constants
AGY_DIR = os.path.expanduser("~/.gemini/antigravity-cli")
JSON_FILE = os.path.join(AGY_DIR, "accounts.json")
TOKEN_FILE = os.path.join(AGY_DIR, "antigravity-oauth-token")
LOG_DIR = os.path.join(AGY_DIR, "log")
REAL_AGY = os.path.expanduser("~/.local/bin/agy-bin")

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

def display_len(s):
    double_width_chars = sum(1 for c in s if c in "🟢🔴🟡🟠⭐")
    return len(s) + double_width_chars

def ljust_display(s, width):
    d_len = display_len(s)
    pad = max(0, width - d_len)
    return s + (" " * pad)

def account_display_name(acc, idx):
    return acc.get("email") or acc.get("name") or f"Account {idx + 1}"

def account_key(name):
    return get_username(name).lower()

def strip_ansi(text):
    return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)

def get_model_pct(model_quotas, model_name, default=100):
    quota = model_quotas.get(model_name, {})
    try:
        return int(quota.get("pct", default))
    except (TypeError, ValueError):
        return default

def format_cached_model_usage(acc, model_name):
    model_quotas = acc.get("model_quotas") or {}
    if model_name not in model_quotas:
        return "?"

    quota = model_quotas.get(model_name, {})
    if "five_hour_pct" in quota and "weekly_pct" in quota:
        return f"{quota['five_hour_pct']}%/{quota['weekly_pct']}%"

    pct = get_model_pct(model_quotas, model_name, default=None)
    if pct is None:
        return "?"
    return f"{pct}%"

def format_exact_reset_time(duration_str, base_time=None):
    if not duration_str:
        return ""
    if base_time is None:
        base_time = datetime.now()
    clean_str = duration_str.replace("In ", "").strip()
    if not clean_str:
        return ""
    try:
        delta = parse_duration(clean_str)
        if delta.total_seconds() == 0:
            return duration_str
        reset_time = base_time + delta
        return reset_time.strftime("%a %H:%M")
    except Exception:
        return duration_str

