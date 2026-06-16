import json
import os

from utils import (
    CLAUDE_FALLBACK_MODEL,
    GEMINI_FALLBACK_MODEL,
    format_cached_model_usage,
    get_username,
    ljust_display,
    sort_rows_by_remaining_quota,
)


def active_account_email(accounts, token_file):
    if not os.path.exists(token_file):
        return None
    try:
        with open(token_file, "r") as f:
            token_data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    active_rt = token_data.get("token", {}).get("refresh_token")
    if not active_rt:
        return None

    for account in accounts:
        if account.get("token", {}).get("refresh_token") == active_rt:
            return account.get("email") or account.get("name")
    return None


def shorten_account_label(raw_email, width=20):
    if len(raw_email) <= width:
        return raw_email
    if " ⭐" in raw_email:
        return raw_email[: width - 2] + " ⭐"
    return raw_email[: width - 3] + "..."


def print_live_status_table(rows):
    print("┌────┬──────────────────────┬──────────┬──────────────────┬────────────────────────────┐")
    print("│IDX │ ACCOUNT              │ STATUS   │ QUOTA            │ RESET TIME                 │")
    print("├────┼──────────────────────┼──────────┼──────────────────┼────────────────────────────┤")
    for row in sort_rows_by_remaining_quota(rows):
        idx_str = f"{row['index'] + 1}".center(4)
        email_str = shorten_account_label(row["email"])
        email_str_padded = ljust_display(email_str, 20)
        status_str_padded = ljust_display(row["status"], 8)
        quota_str_padded = ljust_display(row["quota"], 16)
        reset_str_padded = ljust_display(row["reset_info"], 26)
        print(f"│{idx_str}│ {email_str_padded} │ {status_str_padded} │ {quota_str_padded} │ {reset_str_padded} │")
    print("└────┴──────────────────────┴──────────┴──────────────────┴────────────────────────────┘")
    print("(* Quota shows account readiness. ⭐ indicates active account. 5H = 5-Hour Session Limit, W = Weekly Limit.)")


def print_account_usage_table(accounts, token_file):
    active_email = active_account_email(accounts, token_file)
    print("┌─────┬──────────────────────┬──────────┬─────────────┬─────────────┐")
    print("│ IDX │ ACCOUNT              │ ACTIVE   │ GEMINI 5H/W │ OPUS 5H/W   │")
    print("├─────┼──────────────────────┼──────────┼─────────────┼─────────────┤")
    for idx, account in enumerate(accounts):
        name = account.get("email") or account.get("name") or f"Account {idx}"
        idx_str = f"{idx + 1}".center(5)
        name_padded = ljust_display(shorten_account_label(name), 20)
        is_active = "⭐" if active_email and get_username(name) == get_username(active_email) else ""
        active_padded = ljust_display(is_active, 8)
        gemini_usage = format_cached_model_usage(account, GEMINI_FALLBACK_MODEL)
        opus_usage = format_cached_model_usage(account, CLAUDE_FALLBACK_MODEL)
        gemini_padded = ljust_display(gemini_usage, 11)
        opus_padded = ljust_display(opus_usage, 11)
        print(f"│{idx_str}│ {name_padded} │ {active_padded} │ {gemini_padded} │ {opus_padded} │")
    print("└─────┴──────────────────────┴──────────┴─────────────┴─────────────┘")
    print("Gemini = Gemini 3.5 Flash (High); Opus = Claude Opus 4.6 (Thinking).")
    print("5H/W = 5-Hour Session Limit / Weekly Limit. '?' means run 'agy status' to refresh.")
