import json
import os

from parser import get_weekly_usage
from presentation import print_account_usage_table
from storage import write_accounts
from utils import AGY_DIR, JSON_FILE, TOKEN_FILE, ljust_display


def list_accounts():
    if not os.path.exists(JSON_FILE):
        print(f"❌ accounts.json not found at {JSON_FILE}")
        return

    with open(JSON_FILE, "r") as handle:
        accounts = json.load(handle)

    if not accounts:
        print("❌ No accounts in accounts.json!")
        return

    print_account_usage_table(accounts, TOKEN_FILE)


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


def _resolve_legacy_account(accounts, target):
    if target.isdigit():
        index = int(target) - 1
        if 0 <= index < len(accounts):
            return index
        print(f"❌ Index {target} out of range (1 to {len(accounts)}).")
        return None

    target_lower = target.lower()
    matches = []
    for index, account in enumerate(accounts):
        email = account.get("email") or account.get("name") or ""
        if target_lower in email.lower():
            matches.append((index, email))

    if not matches:
        print(f"❌ No account found matching: '{target}'")
        return None
    if len(matches) > 1:
        print(f"⚠️ Multiple accounts matched '{target}':")
        for index, email in matches:
            print(f"  [{index}] {email}")
        print("Please specify a more precise email or use the index.")
        return None
    return matches[0][0]


def select_account(target):
    if not os.path.exists(JSON_FILE):
        print(f"❌ accounts.json not found at {JSON_FILE}")
        return

    with open(JSON_FILE, "r") as handle:
        accounts = json.load(handle)

    if not accounts:
        print("❌ No accounts in accounts.json!")
        return

    matched_idx = _resolve_legacy_account(accounts, target)
    if matched_idx is None:
        return

    selected_account = accounts[matched_idx]
    with open(TOKEN_FILE, "w") as handle:
        json.dump(selected_account, handle)

    next_index = (matched_idx + 1) % len(accounts)
    with open(os.path.join(AGY_DIR, ".current_index"), "w") as handle:
        handle.write(str(next_index))

    email = selected_account.get("email") or selected_account.get("name") or f"Account {matched_idx}"
    print(f"🟢 Switched active account to: {email} (Index: [{matched_idx + 1}])")


def _print_removable_accounts(accounts):
    print("\n👥 Available Accounts:")
    print("┌─────┬──────────────────────┐")
    print("│ IDX │ ACCOUNT NAME         │")
    print("├─────┼──────────────────────┤")
    for index, account in enumerate(accounts):
        name = account.get("email") or account.get("name") or f"Account {index}"
        idx_str = f"{index + 1}".center(5)
        name_padded = name.ljust(20)[:20]
        print(f"│{idx_str}│ {name_padded} │")
    print("└─────┴──────────────────────┘")
    print("To remove, run: agy remove-account <idx> or agy remove-account <email_or_name>")


def remove_account(target=None):
    if not os.path.exists(JSON_FILE):
        print(f"❌ accounts.json not found at {JSON_FILE}")
        return

    with open(JSON_FILE, "r") as handle:
        accounts = json.load(handle)

    if not accounts:
        print("❌ No accounts in accounts.json!")
        return

    if target is None:
        _print_removable_accounts(accounts)
        return

    matched_idx = _resolve_legacy_account(accounts, target)
    if matched_idx is None:
        return

    removed_account = accounts.pop(matched_idx)
    removed_name = removed_account.get("email") or removed_account.get("name") or f"Account {matched_idx}"
    write_accounts(accounts)

    print(f"🗑️ Successfully removed account: {removed_name} (Index: [{matched_idx}])")

    index_file = os.path.join(AGY_DIR, ".current_index")
    if os.path.exists(index_file):
        try:
            with open(index_file, "r") as handle:
                current_index = int(handle.read().strip())
            next_index = 0 if current_index >= len(accounts) else current_index
            with open(index_file, "w") as handle:
                handle.write(str(next_index))
        except Exception:
            pass
