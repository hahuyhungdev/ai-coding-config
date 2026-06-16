import json
import os
import re
import subprocess

from storage import normalize_token_payload, upsert_account_token, write_accounts
from utils import JSON_FILE, LOG_DIR, REAL_AGY, TOKEN_FILE, get_username


def _load_accounts_permissive():
    if not os.path.exists(JSON_FILE):
        return []
    try:
        with open(JSON_FILE, "r") as handle:
            return json.load(handle)
    except Exception:
        return []


def _detect_email_from_recent_logs():
    subprocess.run(
        [REAL_AGY, "-p", "ping connection check - say pong"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    log_files = []
    if os.path.exists(LOG_DIR):
        for filename in os.listdir(LOG_DIR):
            if filename.startswith("cli-") and filename.endswith(".log"):
                path = os.path.join(LOG_DIR, filename)
                log_files.append((path, os.path.getmtime(path)))
    log_files.sort(key=lambda item: item[1], reverse=True)

    if not log_files:
        return None

    try:
        with open(log_files[0][0], "r", errors="ignore") as handle:
            for _ in range(200):
                line = handle.readline()
                if not line:
                    break
                if "applyAuthResult" in line and "email=" in line:
                    match = re.search(r"email=([^,\s]+)", line)
                    if match:
                        return match.group(1)
    except Exception:
        return None
    return None


def import_current_token(custom_email=None):
    if not os.path.exists(TOKEN_FILE):
        print(f"❌ No active token file found at {TOKEN_FILE}")
        print("Please log in or run 'agy' first to generate a token.")
        return

    try:
        with open(TOKEN_FILE, "r") as handle:
            current_data = json.load(handle)
    except Exception as exc:
        print(f"❌ Failed to parse token file: {exc}")
        return

    email = custom_email or current_data.get("email")
    if not email:
        print("⏳ Auto-detecting email from active session...")
        email = _detect_email_from_recent_logs()

    if not email:
        print("❌ Could not auto-detect email. Please specify your account name:")
        print("   agy add-current <email_or_name>")
        return

    username = get_username(email)
    accounts = _load_accounts_permissive()

    try:
        token_obj, auth_method, _ = normalize_token_payload(current_data, fallback_email=email)
    except ValueError as exc:
        print(f"❌ {exc}")
        return

    updated = upsert_account_token(accounts, email, token_obj, auth_method)
    if not updated:
        print(f"🟢 Successfully added new account '{username}' to accounts.json!")
    else:
        print(f"🟢 Successfully updated existing account '{username}' in accounts.json!")

    write_accounts(accounts)


def add_token_from_input(custom_email=None):
    print("📋 Paste your token JSON below, then press Ctrl+D (Linux/Mac) or Ctrl+Z (Windows):")
    print()

    lines = []
    try:
        while True:
            lines.append(input())
    except EOFError:
        pass

    raw = "\n".join(lines).strip()
    if not raw:
        print("❌ No input received.")
        return

    try:
        token_data = json.loads(raw)
    except Exception as exc:
        print(f"❌ Invalid JSON: {exc}")
        return

    accounts = _load_accounts_permissive()
    try:
        token_obj, auth_method, email = normalize_token_payload(token_data, fallback_email=custom_email)
    except ValueError as exc:
        if "refresh_token" in str(exc):
            print("❌ No refresh_token found in the JSON.")
        else:
            print("❌ Invalid token. Expected JSON with 'refresh_token' or 'token' key.")
        return

    if not email:
        email = input("📧 Enter account name/email label: ").strip()
        if not email:
            email = "account-" + str(len(accounts))
            print(f"⏳ Using default label: '{email}'")

    username = get_username(email)
    updated = upsert_account_token(
        accounts,
        username,
        token_obj,
        auth_method,
        include_alias_label=False,
    )

    if not updated:
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
        with open(file_path, "r") as handle:
            token_data = json.load(handle)
    except Exception as exc:
        print(f"❌ Failed to parse JSON: {exc}")
        return

    accounts = _load_accounts_permissive()
    try:
        token_obj, auth_method, email = normalize_token_payload(token_data, fallback_email=custom_email)
    except ValueError as exc:
        if "refresh_token" in str(exc):
            print("❌ No refresh_token found in the file.")
        else:
            print("❌ Invalid token file. Expected JSON with 'refresh_token' or 'token' key.")
        return

    if not email:
        basename = os.path.splitext(os.path.basename(file_path))[0]
        email = basename
        print(f"⏳ No email specified, using filename as label: '{email}'")

    username = get_username(email)
    updated = upsert_account_token(
        accounts,
        username,
        token_obj,
        auth_method,
        include_alias_label=False,
    )

    if not updated:
        print(f"🟢 Added new account '{username}' from {os.path.basename(file_path)}!")
    else:
        print(f"🟢 Updated existing account '{username}' with token from {os.path.basename(file_path)}!")

    write_accounts(accounts)
    print(f"   Total accounts: {len(accounts)}")
