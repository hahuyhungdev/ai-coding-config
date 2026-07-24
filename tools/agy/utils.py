import os
import re
from datetime import datetime, timedelta

# Constants
def sync_utils_paths():
    global AGY_DIR, JSON_FILE, TOKEN_FILE, LOG_DIR, REAL_AGY
    is_mocked = os.environ.get("AGY_TESTING") == "1" and ("antigravity-cli" not in JSON_FILE or "tmp" in JSON_FILE or "sandbox" in JSON_FILE)
    if is_mocked:
        return
    AGY_DIR = os.environ.get("AGY_DIR_OVERRIDE", os.path.expanduser("~/.gemini/antigravity-cli"))
    JSON_FILE = os.path.join(AGY_DIR, "accounts.json")
    TOKEN_FILE = os.path.join(AGY_DIR, "antigravity-oauth-token")
    LOG_DIR = os.path.join(AGY_DIR, "log")
    REAL_AGY = os.path.expanduser("~/.local/bin/agy-bin")

AGY_DIR = os.environ.get("AGY_DIR_OVERRIDE", os.path.expanduser("~/.gemini/antigravity-cli"))
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

def get_session_state_dir(create=False):
    state_dir = os.environ.get("AGY_WRAPPER_STATE_DIR")
    if state_dir:
        if create:
            os.makedirs(state_dir, mode=0o700, exist_ok=True)
        return state_dir
    return AGY_DIR

def session_state_path(filename, create_dir=False):
    state_dir = get_session_state_dir(create=create_dir)
    return os.path.join(state_dir, filename)

def get_session_token_file(default_token_file=None):
    token_file = os.environ.get("AGY_SESSION_TOKEN_FILE")
    if token_file and os.path.exists(token_file):
        return token_file
    return default_token_file or TOKEN_FILE

def get_session_log_file():
    log_file = os.environ.get("AGY_SESSION_LOG_FILE")
    if log_file and os.path.exists(log_file):
        return log_file

    active_log_path = session_state_path("active_log_path")
    if os.path.exists(active_log_path):
        try:
            stored = open(active_log_path, "r", encoding="utf-8").read().strip()
        except OSError:
            stored = ""
        if stored and os.path.exists(stored):
            return stored
    return None

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
    return acc.get("label") or acc.get("email") or acc.get("name") or f"Account {idx + 1}"

def account_key(name):
    return get_username(name).lower()

def strip_ansi(text):
    return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)

def is_provider_quota_error_line(line):
    text = str(line or "")
    text_lower = text.lower()
    stripped = text.lstrip()

    quota_terms = (
        "resource_exhausted",
        "quota exceeded",
        "individual quota reached",
        "too many tokens",
        "rate limit",
    )
    if not any(term in text_lower for term in quota_terms):
        if not ("429" in text_lower and ("quota" in text_lower or "rate limit" in text_lower)):
            return False

    if stripped.startswith(("+", "-", ">", "|")):
        return False
    if "check_for_quota_error(" in text_lower or "<compaction_rollover" in text_lower:
        return False
    if (
        "telemetry setting" in text_lower
        or "propagate telemetry" in text_lower
        or "cli_setting_manager" in text_lower
    ):
        return False

    if re.match(r"^[EWF]\d{4}\s+\d{2}:\d{2}:\d{2}", stripped):
        return True

    if "resource_exhausted" in text_lower and (
        "code" in text_lower or "resets in" in text_lower or "quota" in text_lower
    ):
        return True

    provider_context = (
        re.search(r"\berror\b", text_lower)
        or "exception" in text_lower
        or "failed" in text_lower
        or "resets in" in text_lower
        or "code" in text_lower
        or "429" in text_lower
    )
    if provider_context and (
        "quota exceeded" in text_lower
        or "individual quota reached" in text_lower
        or "too many tokens" in text_lower
        or "rate limit" in text_lower
    ):
        return True

    return False

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

def remaining_quota_value(quota_text):
    percentages = re.findall(r"(\d+)%", str(quota_text or ""))
    if not percentages:
        return -1
    return min(int(pct) for pct in percentages)

def parse_quota_percentages(quota_text):
    """Parses 5H and W percentages from quota_text.
    Returns (five_hour_pct, weekly_pct) where value is -1 if not found.
    """
    text = str(quota_text or "")
    five_hour_pct = -1
    m_5h = re.search(r"5H:(\d+)%", text)
    if m_5h:
        five_hour_pct = int(m_5h.group(1))

    weekly_pct = -1
    m_w = re.search(r"W:(\d+)%", text)
    if m_w:
        weekly_pct = int(m_w.group(1))

    if five_hour_pct == -1 or weekly_pct == -1:
        percentages = [int(p) for p in re.findall(r"(\d+)%", text)]
        if len(percentages) >= 2:
            five_hour_pct, weekly_pct = percentages[0], percentages[1]
        elif len(percentages) == 1:
            five_hour_pct = weekly_pct = percentages[0]

    return five_hour_pct, weekly_pct

def get_account_reset_seconds(account):
    default_large = 99999999

    blocked_until = account.get("blocked_until")
    if blocked_until:
        try:
            dt = datetime.fromisoformat(blocked_until)
            diff = (dt - datetime.now()).total_seconds()
            return max(0, int(diff))
        except:
            pass

    model_quotas = account.get("model_quotas") or {}
    if not model_quotas:
        reset_info = account.get("reset_info") or ""
        if "In " in reset_info:
            try:
                delta = parse_duration(reset_info.replace("In ", ""))
                return int(delta.total_seconds())
            except:
                pass
        return default_large

    rep_model = None
    for preferred in ["Gemini 3.5 Flash (Medium)", "Gemini 3.5 Flash (High)"]:
        if preferred in model_quotas:
            rep_model = preferred
            break
    if not rep_model:
        if model_quotas.keys():
            rep_model = next(iter(model_quotas.keys()))
        else:
            return default_large

    quota = model_quotas[rep_model]

    if "weekly_pct" in quota and "five_hour_pct" in quota:
        weekly_pct = quota["weekly_pct"]
        five_hour_pct = quota["five_hour_pct"]
        weekly_refresh = quota.get("weekly_refresh", "")
        five_hour_refresh = quota.get("five_hour_refresh", "")

        if five_hour_pct < weekly_pct:
            if five_hour_refresh and five_hour_refresh.startswith("In "):
                try:
                    return int(parse_duration(five_hour_refresh.replace("In ", "")).total_seconds())
                except:
                    pass
            return 0
        else:
            if weekly_refresh and weekly_refresh.startswith("In "):
                try:
                    return int(parse_duration(weekly_refresh.replace("In ", "")).total_seconds())
                except:
                    pass
            return 0

    refresh = quota.get("refresh", "")
    if refresh and refresh.startswith("In "):
        try:
            return int(parse_duration(refresh.replace("In ", "")).total_seconds())
        except:
            pass

    return 0

def sort_rows_by_remaining_quota(rows):
    return sorted(
        rows,
        key=lambda row: (
            remaining_quota_value(row.get("quota")),
            -row.get("reset_seconds", 99999999)
        ),
        reverse=True,
    )

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

def clear_mcp_token_cache():
    import os
    for cache_name in ["mcp-oauth-tokens-v2.json", "mcp-oauth-tokens.json"]:
        cache_file = os.path.expanduser(f"~/.gemini/{cache_name}")
        if os.path.exists(cache_file):
            try:
                os.unlink(cache_file)
            except OSError:
                pass
