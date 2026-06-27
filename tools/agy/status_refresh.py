import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from parser import get_remaining_reset_from_logs, parse_quota_output
from presentation import print_live_status_table
from pty_client import get_quota_via_pty
from storage import write_accounts
from utils import (
    AGY_DIR,
    JSON_FILE,
    TOKEN_FILE,
    format_exact_reset_time,
    get_username,
    parse_duration,
)


def find_duplicate_refresh_tokens(accounts):
    """Map duplicate account indexes to the first account using that token."""
    first_seen = {}
    duplicates = {}
    for index, account in enumerate(accounts):
        refresh_token = account.get("token", {}).get("refresh_token")
        if not refresh_token:
            continue
        if refresh_token in first_seen:
            duplicates[index] = first_seen[refresh_token]
        else:
            first_seen[refresh_token] = index
    return duplicates


def _original_token_state(accounts):
    if not os.path.exists(TOKEN_FILE):
        return None, None
    try:
        with open(TOKEN_FILE, "r") as handle:
            raw_token = handle.read()
        token_data = json.loads(raw_token)
    except (OSError, json.JSONDecodeError):
        return None, None

    active_rt = token_data.get("token", {}).get("refresh_token")
    active_email = token_data.get("email") or token_data.get("name")
    if not active_email and active_rt:
        for account in accounts:
            if account.get("token", {}).get("refresh_token") == active_rt:
                active_email = account.get("email") or account.get("name")
                break
    return token_data, active_email


def _quota_summary(model_quotas):
    if not model_quotas:
        return "100%", ""

    rep_model = None
    for preferred in ["Gemini 3.5 Flash (Medium)", "Gemini 3.5 Flash (High)"]:
        if preferred in model_quotas:
            rep_model = preferred
            break
            
    if not rep_model:
        rep_model = next(iter(model_quotas.keys()))

    quota = model_quotas[rep_model]
    if "weekly_pct" in quota and "five_hour_pct" in quota:
        weekly_pct = quota["weekly_pct"]
        five_hour_pct = quota["five_hour_pct"]
        weekly_refresh = quota.get("weekly_refresh", "")
        five_hour_refresh = quota.get("five_hour_refresh", "")
        five_hour_clean = format_exact_reset_time(five_hour_refresh) if five_hour_refresh else "Ready"
        weekly_clean = format_exact_reset_time(weekly_refresh) if weekly_refresh else "Ready"
        return f"5H:{five_hour_pct}%/W:{weekly_pct}%", f"5H:{five_hour_clean}/W:{weekly_clean}"
    quota_text = f"{quota['pct']}%"
    reset_text = format_exact_reset_time(quota["refresh"]) if quota.get("refresh") else ""
    return quota_text, reset_text


def _blocked_until(status, model_quotas, raw_reset):
    if status != "🔴 Blocked":
        return None

    max_delta = timedelta(0)
    for quota in model_quotas.values():
        for refresh_key in ["refresh", "weekly_refresh", "five_hour_refresh"]:
            refresh_value = quota.get(refresh_key, "")
            if not refresh_value or not refresh_value.startswith("In "):
                continue
            try:
                max_delta = max(max_delta, parse_duration(refresh_value.replace("In ", "")))
            except Exception:
                pass

    if raw_reset:
        try:
            max_delta = max(max_delta, parse_duration(raw_reset.replace("In ", "")))
        except Exception:
            pass

    if max_delta.total_seconds() <= 0:
        return None
    return (datetime.now() + max_delta).isoformat()


def _check_single_account(index, account, accounts, duplicate_tokens, active_email, original_token=None):
    email = account.get("email") or account.get("name") or f"Account {index}"

    if index in duplicate_tokens:
        original_idx = duplicate_tokens[index]
        return {
            "idx": index,
            "email": email,
            "status": "🟡 Dup",
            "quota": f"Same as #{original_idx + 1}",
            "reset_info": "",
            "refreshed_token": None,
            "model_quotas": {},
            "blocked_until": None,
        }

    print(f"⏳ Checking status for {email}...", flush=True)

    sandbox_dir = os.path.join(AGY_DIR, f"scratch/sandbox_{index}")
    sandbox_gemini_dir = os.path.join(sandbox_dir, ".gemini/antigravity-cli")
    os.makedirs(sandbox_gemini_dir, exist_ok=True)

    sandbox_token_file = os.path.join(sandbox_gemini_dir, "antigravity-oauth-token")
    token_to_write = account
    if active_email and original_token and get_username(email) == get_username(active_email):
        token_to_write = original_token

    with open(sandbox_token_file, "w") as handle:
        json.dump(token_to_write, handle)

    global_cache = os.path.join(AGY_DIR, "cache")
    if os.path.exists(global_cache):
        try:
            shutil.copytree(global_cache, os.path.join(sandbox_gemini_dir, "cache"))
        except Exception:
            pass

    real_settings = os.path.join(AGY_DIR, "settings.json")
    if os.path.exists(real_settings):
        try:
            shutil.copy2(real_settings, os.path.join(sandbox_gemini_dir, "settings.json"))
        except Exception:
            pass

    real_inst_id = os.path.join(AGY_DIR, "installation_id")
    if os.path.exists(real_inst_id):
        try:
            shutil.copy2(real_inst_id, os.path.join(sandbox_gemini_dir, "installation_id"))
        except Exception:
            pass

    output = get_quota_via_pty(email, sandbox_dir=sandbox_dir)

    refreshed_token = None
    try:
        with open(sandbox_token_file, "r") as handle:
            refreshed_account = json.load(handle)
            refreshed_token = refreshed_account.get("token")
    except Exception:
        pass

    try:
        shutil.rmtree(sandbox_dir)
    except Exception:
        pass

    status = "🔴 Blocked"
    quota_text = "0%"
    reset_text = ""
    raw_reset = ""
    model_quotas = {}

    has_quota_screen = (
        "Model Quota" in output
        or "Model Usage" in output
        or "Quota" in output
        or "GEMINI MODELS" in output
        or "CLAUDE AND GPT MODELS" in output
    )

    if has_quota_screen:
        status = "🟢 Ready"
        model_quotas = parse_quota_output(output)
        if model_quotas:
            quota_text, reset_text = _quota_summary(model_quotas)
            if all(model["pct"] == 0 for model in model_quotas.values()):
                status = "🔴 Blocked"
                quota_text = "0%"
    else:
        raw_reset = get_remaining_reset_from_logs(email, accounts)
        if raw_reset:
            status = "🔴 Blocked"
            quota_text = "🔴 0% (Blocked)"
            reset_text = f"5H:{format_exact_reset_time(raw_reset)}/W:Ready"
        else:
            status = "🟢 Ready"
            quota_text = "100%"

    active_marker = " ⭐" if active_email and get_username(email) == get_username(active_email) else ""
    return {
        "idx": index,
        "email": email + active_marker,
        "status": status,
        "quota": quota_text,
        "reset_info": reset_text,
        "refreshed_token": refreshed_token,
        "model_quotas": model_quotas,
        "blocked_until": _blocked_until(status, model_quotas, raw_reset),
    }


def _apply_status_result(accounts, result):
    index = result["idx"]
    if result["refreshed_token"]:
        accounts[index]["token"] = result["refreshed_token"]

    accounts[index]["status"] = result["status"]
    accounts[index]["quota"] = result["quota"]
    accounts[index]["reset_info"] = result["reset_info"]
    accounts[index]["last_checked"] = datetime.now().isoformat()
    if result["blocked_until"]:
        accounts[index]["blocked_until"] = result["blocked_until"]
    else:
        accounts[index].pop("blocked_until", None)
    accounts[index]["model_quotas"] = result["model_quotas"]

    return {
        "index": index,
        "email": result["email"],
        "status": result["status"],
        "quota": result["quota"],
        "reset_info": result["reset_info"],
    }


def get_account_status():
    if not os.path.exists(JSON_FILE):
        print(f"❌ accounts.json not found at {JSON_FILE}")
        return

    with open(JSON_FILE, "r") as handle:
        accounts = json.load(handle)

    original_token, active_email = _original_token_state(accounts)
    duplicate_tokens = find_duplicate_refresh_tokens(accounts)
    status_report = []

    try:
        results = []
        workers = min(max(1, len(accounts) - len(duplicate_tokens)), 8)
        if workers > 0:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [
                    executor.submit(
                        _check_single_account,
                        index,
                        account,
                        accounts,
                        duplicate_tokens,
                        active_email,
                        original_token,
                    )
                    for index, account in enumerate(accounts)
                ]
                for future in futures:
                    results.append(future.result())
        else:
            for index, account in enumerate(accounts):
                results.append(_check_single_account(index, account, accounts, duplicate_tokens, active_email, original_token))

        results.sort(key=lambda result: result["idx"])
        for result in results:
            status_report.append(_apply_status_result(accounts, result))

        write_accounts(accounts, create_backup=False)
    finally:
        if original_token is not None:
            with open(TOKEN_FILE, "w") as handle:
                json.dump(original_token, handle)

    print(" " * 80, end="\r", flush=True)
    print_live_status_table(status_report)
