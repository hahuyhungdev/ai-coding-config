import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from utils import AGY_DIR, JSON_FILE, TOKEN_FILE, account_display_name


BACKUP_DIR = os.path.join(AGY_DIR, "backups")


def load_accounts():
    if not os.path.exists(JSON_FILE):
        return []
    if os.path.exists(JSON_FILE) and os.path.getsize(JSON_FILE) == 0:
        return []
    with open(JSON_FILE, "r") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("accounts.json must contain a JSON array")
    return data


def backup_accounts(output_path=None):
    if not os.path.exists(JSON_FILE):
        return None

    if output_path:
        destination = Path(output_path).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
    else:
        Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        destination = Path(BACKUP_DIR) / f"accounts-{timestamp}.json"

    shutil.copy2(JSON_FILE, destination)
    os.chmod(destination, 0o600)
    shutil.copy2(JSON_FILE, os.path.join(AGY_DIR, "accounts-backup.json"))
    os.chmod(os.path.join(AGY_DIR, "accounts-backup.json"), 0o600)
    return str(destination)


def write_accounts(accounts, create_backup=True):
    Path(AGY_DIR).mkdir(parents=True, exist_ok=True)
    backup_path = backup_accounts() if create_backup else None
    temporary = Path(JSON_FILE + ".tmp")
    temporary.write_text(json.dumps(accounts, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, JSON_FILE)
    return backup_path


def normalize_token_payload(token_data, fallback_email=None):
    if "token" in token_data and isinstance(token_data["token"], dict):
        token_obj = token_data["token"]
        auth_method = token_data.get("auth_method", "consumer")
        email = fallback_email or token_data.get("email")
    elif "refresh_token" in token_data:
        token_obj = token_data
        auth_method = "consumer"
        email = fallback_email
    else:
        raise ValueError("Expected JSON with 'refresh_token' or 'token' key")

    if not token_obj.get("refresh_token"):
        raise ValueError("No refresh_token found")

    return token_obj, auth_method, email


def upsert_account_token(accounts, email, token_obj, auth_method, include_alias_label=True):
    from utils import get_username

    username = get_username(email)
    updated = False
    for index, account in enumerate(accounts):
        account_email = account.get("email") or account.get("name") or ""
        if get_username(account_email) == username:
            accounts[index]["token"] = token_obj
            accounts[index]["auth_method"] = auth_method
            if "@" in email:
                accounts[index]["email"] = email
            updated = True
            break

    if not updated:
        account = {
            "email": email if "@" in email else username,
            "auth_method": auth_method,
            "token": token_obj,
        }
        if include_alias_label:
            account["label"] = None if "@" in email else username
        accounts.append(account)

    return updated


def resolve_account(accounts, target):
    if not accounts:
        raise ValueError("No accounts configured")
    if str(target).isdigit():
        index = int(target) - 1
        if 0 <= index < len(accounts):
            return index
        raise ValueError(f"Index {target} out of range (1 to {len(accounts)})")

    target_lower = str(target).lower()
    matches = []
    for index, account in enumerate(accounts):
        values = [account.get("label"), account.get("email"), account.get("name")]
        if any(target_lower in value.lower() for value in values if value):
            matches.append(index)
    if not matches:
        raise ValueError(f"No account found matching '{target}'")
    if len(matches) > 1:
        raise ValueError(f"Multiple accounts match '{target}'")
    return matches[0]


def active_account_index(accounts):
    if not os.path.exists(TOKEN_FILE):
        return None
    try:
        token_data = json.loads(Path(TOKEN_FILE).read_text(encoding="utf-8"))
        active_token = (token_data.get("token") or token_data).get("refresh_token")
    except (OSError, ValueError, AttributeError):
        return None
    if not active_token:
        return None
    for index, account in enumerate(accounts):
        if account.get("token", {}).get("refresh_token") == active_token:
            return index
    return None


def public_accounts(accounts):
    active_index = active_account_index(accounts)
    rows = []
    for index, account in enumerate(accounts):
        rows.append({
            "index": index + 1,
            "label": account.get("label"),
            "email": account.get("email") or account.get("name"),
            "display": account_display_name(account, index),
            "active": index == active_index,
            "status": account.get("status", "Unknown"),
            "quota": account.get("quota", "?"),
            "reset_time": account.get("reset_info", ""),
            "last_checked": account.get("last_checked"),
            "token_available": bool(account.get("token", {}).get("refresh_token")),
        })
    return rows


def restore_accounts(source_path=None):
    if source_path:
        source = Path(source_path).expanduser().resolve()
    else:
        backups = sorted(Path(BACKUP_DIR).glob("accounts-*.json"), reverse=True)
        if not backups:
            raise ValueError("No account backup found")
        source = backups[0]
    if not source.is_file():
        raise ValueError(f"Backup not found: {source}")
    restored = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(restored, list):
        raise ValueError("Backup must contain a JSON array")
    previous_backup = write_accounts(restored, create_backup=True)
    return str(source), previous_backup


def doctor_report():
    issues = []
    try:
        accounts = load_accounts()
        accounts_valid = True
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        accounts = []
        accounts_valid = False
        issues.append(str(exc))

    missing_tokens = sum(
        1 for account in accounts
        if not account.get("token", {}).get("refresh_token")
    )
    if not os.path.exists(JSON_FILE):
        issues.append("accounts.json is missing")
    if not os.path.exists(TOKEN_FILE):
        issues.append("active token file is missing")
    if missing_tokens:
        issues.append(f"{missing_tokens} account(s) have no refresh token")

    return {
        "ok": accounts_valid and os.path.exists(JSON_FILE) and missing_tokens == 0,
        "accounts_file": JSON_FILE,
        "accounts_file_exists": os.path.exists(JSON_FILE),
        "accounts_valid": accounts_valid,
        "account_count": len(accounts),
        "active_token_exists": os.path.exists(TOKEN_FILE),
        "backup_directory": BACKUP_DIR,
        "backup_count": len(list(Path(BACKUP_DIR).glob("accounts-*.json"))) if os.path.isdir(BACKUP_DIR) else 0,
        "issues": issues,
    }


def sync_active_token_to_accounts():
    if not os.path.exists(TOKEN_FILE) or not os.path.exists(JSON_FILE):
        return
    if os.path.getsize(TOKEN_FILE) == 0 or os.path.getsize(JSON_FILE) == 0:
        return
    try:
        with open(TOKEN_FILE, "r") as f:
            current_data = json.load(f)
        with open(JSON_FILE, "r") as f:
            accounts = json.load(f)
    except Exception:
        return

    email = current_data.get("email") or current_data.get("name")
    if not email:
        return

    try:
        token_obj, auth_method, _ = normalize_token_payload(current_data, fallback_email=email)
    except ValueError:
        return

    from utils import get_username
    username = get_username(email)
    updated = False
    for index, account in enumerate(accounts):
        account_email = account.get("email") or account.get("name") or ""
        if get_username(account_email) == username:
            if account.get("token") != token_obj:
                accounts[index]["token"] = token_obj
                accounts[index]["auth_method"] = auth_method
                updated = True
            break

    if updated:
        write_accounts(accounts, create_backup=False)
