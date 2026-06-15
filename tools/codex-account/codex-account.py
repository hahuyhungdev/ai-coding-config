#!/usr/bin/env python3
import argparse
import base64
import getpass
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def codex_home():
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def accounts_path():
    return Path(os.environ.get("CODEX_ACCOUNTS_FILE", codex_home() / "accounts.json")).expanduser()


def auth_path():
    return Path(os.environ.get("CODEX_AUTH_FILE", codex_home() / "auth.json")).expanduser()


def sessions_dir():
    return Path(os.environ.get("CODEX_SESSIONS_DIR", codex_home() / "sessions")).expanduser()


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def write_private_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def backup_file(path):
    if not path.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.name}.bak-{stamp}")
    shutil.copy2(path, backup)
    os.chmod(backup, 0o600)
    return backup


def is_auth_blob(payload):
    return isinstance(payload, dict) and isinstance(payload.get("tokens"), dict)


def account_id(auth_blob):
    tokens = auth_blob.get("tokens") or {}
    return tokens.get("account_id") or ""


def decode_jwt_payload(token):
    if not token or token.count(".") < 2:
        return {}
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")))
    except (ValueError, json.JSONDecodeError):
        return {}


def token_claims(auth_blob):
    tokens = auth_blob.get("tokens") or {}
    claims = {}
    for token_key in ("id_token", "access_token"):
        claims.update(decode_jwt_payload(tokens.get(token_key)))
    return claims


def account_email(auth_blob):
    claims = token_claims(auth_blob)
    profile = claims.get("https://api.openai.com/profile") or {}
    return claims.get("email") or profile.get("email") or ""


def account_name(auth_blob):
    claims = token_claims(auth_blob)
    return claims.get("name") or claims.get("preferred_username") or claims.get("username") or ""


def account_plan(auth_blob):
    auth = token_claims(auth_blob).get("https://api.openai.com/auth") or {}
    return auth.get("chatgpt_plan_type") or ""


def parse_timestamp(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def format_rate_window(window):
    if not isinstance(window, dict):
        return "?"
    used = window.get("used_percent")
    if used is None:
        return "?"
    try:
        return f"{int(round(float(used)))}%"
    except (TypeError, ValueError):
        return "?"


def format_quota(rate_limits):
    if not isinstance(rate_limits, dict):
        return "?"
    primary = format_rate_window(rate_limits.get("primary"))
    secondary = format_rate_window(rate_limits.get("secondary"))
    if primary == "?" and secondary == "?":
        credits = rate_limits.get("credits") or {}
        balance = credits.get("balance")
        return f"credits:{balance}" if balance not in (None, "") else "?"
    return f"5H:{primary}/W:{secondary}"


def format_reset_window(window):
    if not isinstance(window, dict):
        return "?"
    resets_at = window.get("resets_at")
    if not resets_at:
        return "?"
    try:
        return datetime.fromtimestamp(int(resets_at)).astimezone().strftime("%a %H:%M")
    except (OSError, OverflowError, TypeError, ValueError):
        return "?"


def format_reset_time(rate_limits):
    if not isinstance(rate_limits, dict):
        return "?"
    primary = format_reset_window(rate_limits.get("primary"))
    secondary = format_reset_window(rate_limits.get("secondary"))
    if primary == "?" and secondary == "?":
        return "?"
    return f"5H:{primary}/W:{secondary}"


def has_quota_windows(rate_limits):
    return isinstance(rate_limits, dict) and (
        isinstance(rate_limits.get("primary"), dict) or isinstance(rate_limits.get("secondary"), dict)
    )


def latest_rate_limits_by_plan():
    base = sessions_dir()
    if not base.is_dir():
        return {}, None

    latest_by_plan = {}
    latest_any = None
    files = sorted(base.glob("**/*.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line in reversed(lines):
            if '"rate_limits"' not in line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = event.get("payload") or {}
            rate_limits = payload.get("rate_limits")
            if not isinstance(rate_limits, dict):
                continue
            if not has_quota_windows(rate_limits):
                continue
            timestamp = parse_timestamp(event.get("timestamp")) or datetime.fromtimestamp(
                path.stat().st_mtime,
                timezone.utc,
            )
            snapshot = {"timestamp": timestamp, "rate_limits": rate_limits}
            if latest_any is None or timestamp > latest_any["timestamp"]:
                latest_any = snapshot
            plan = rate_limits.get("plan_type")
            if plan and plan != "unknown":
                previous = latest_by_plan.get(plan)
                if previous is None or timestamp > previous["timestamp"]:
                    latest_by_plan[plan] = snapshot
    return latest_by_plan, latest_any


def validate_auth_blob(payload, source):
    if not is_auth_blob(payload):
        raise SystemExit(f"{source} is not a Codex auth JSON object with a tokens object")
    tokens = payload.get("tokens") or {}
    if not tokens.get("refresh_token"):
        raise SystemExit(f"{source} does not include tokens.refresh_token")
    return payload


def infer_label(auth_blob):
    email = account_email(auth_blob)
    if email:
        return email
    account = account_id(auth_blob)
    if account:
        return account[:8]
    return getpass.getuser()


def load_store(migrate=False):
    path = accounts_path()
    payload = load_json(path)
    if payload is None:
        return {"version": 1, "accounts": []}, None

    if isinstance(payload, dict) and isinstance(payload.get("accounts"), list):
        return payload, None

    if is_auth_blob(payload):
        if not migrate:
            return {
                "version": 1,
                "accounts": [{
                    "label": infer_label(payload),
                    "created_at": payload.get("last_refresh") or "",
                    "updated_at": payload.get("last_refresh") or "",
                    "auth": payload,
                }],
            }, None
        backup = backup_file(path)
        store = {
            "version": 1,
            "accounts": [{
                "label": infer_label(payload),
                "created_at": payload.get("last_refresh") or now_iso(),
                "updated_at": payload.get("last_refresh") or now_iso(),
                "auth": payload,
            }],
        }
        write_private_json(path, store)
        return store, backup

    raise SystemExit(
        f"{path} must be either a Codex auth object or a {{version, accounts}} store"
    )


def save_store(store):
    write_private_json(accounts_path(), store)


def active_auth():
    payload = load_json(auth_path())
    return payload if is_auth_blob(payload) else None


def find_account(store, target):
    accounts = store.get("accounts") or []
    if str(target).isdigit():
        index = int(target) - 1
        if 0 <= index < len(accounts):
            return index, accounts[index]
        raise SystemExit(f"Index {target} out of range")

    target_lower = str(target).lower()
    matches = []
    for index, row in enumerate(accounts):
        auth = row.get("auth") or {}
        values = [row.get("label"), account_email(auth), account_name(auth), account_id(auth)]
        if any(target_lower in str(value).lower() for value in values if value):
            matches.append((index, row))

    if not matches:
        raise SystemExit(f"No saved Codex account matches '{target}'")
    if len(matches) > 1:
        labels = ", ".join(row.get("label") or str(index + 1) for index, row in matches)
        raise SystemExit(f"Multiple accounts match '{target}': {labels}")
    return matches[0]


def cmd_list(_args):
    store, _ = load_store(migrate=False)
    current = active_auth()
    current_id = account_id(current) if current else ""
    current_plan = account_plan(current) if current else ""
    latest_by_plan, latest_any = latest_rate_limits_by_plan()

    print("IDX  ACTIVE  LABEL                              PLAN     QUOTA          RESET TIME")
    for index, row in enumerate(store.get("accounts") or [], start=1):
        auth = row.get("auth") or {}
        acc_id = account_id(auth)
        active = "*" if acc_id and acc_id == current_id else ""
        label = row.get("label") or "-"
        plan = account_plan(auth) or "-"
        quota_snapshot = latest_by_plan.get(plan)
        if active and (not quota_snapshot) and latest_any:
            latest_plan = latest_any["rate_limits"].get("plan_type")
            if latest_plan in (None, "unknown", current_plan):
                quota_snapshot = latest_any
        quota = format_quota(quota_snapshot["rate_limits"]) if quota_snapshot else "?"
        reset_time = format_reset_time(quota_snapshot["rate_limits"]) if quota_snapshot else "?"
        print(f"{index:<4} {active:<7} {label:<34} {plan:<8} {quota:<14} {reset_time}")


def read_auth_source(path_text):
    if path_text == "-":
        return validate_auth_blob(json.load(sys.stdin), "stdin")
    path = Path(path_text).expanduser()
    return validate_auth_blob(load_json(path), str(path))


def cmd_add(args):
    auth = read_auth_source(args.source)
    label = args.label or infer_label(auth)
    store, backup = load_store(migrate=True)
    accounts = store.setdefault("accounts", [])

    auth_id = account_id(auth)
    existing_index = None
    for index, row in enumerate(accounts):
        row_auth = row.get("auth") or {}
        if auth_id and account_id(row_auth) == auth_id:
            existing_index = index
            break
        if row.get("label") == label:
            existing_index = index
            break

    timestamp = now_iso()
    if existing_index is None:
        accounts.append({
            "label": label,
            "created_at": timestamp,
            "updated_at": timestamp,
            "auth": auth,
        })
        action = "Added"
    else:
        previous = accounts[existing_index]
        previous["label"] = label
        previous["updated_at"] = timestamp
        previous["auth"] = auth
        action = "Updated"

    save_store(store)
    if backup:
        print(f"Backed up previous accounts.json to {backup}")
    print(f"{action} Codex account '{label}'")


def cmd_use(args):
    store, _ = load_store(migrate=False)
    _, row = find_account(store, args.target)
    auth = validate_auth_blob(row.get("auth"), f"account {args.target}")
    backup = backup_file(auth_path())
    write_private_json(auth_path(), auth)
    if backup:
        print(f"Backed up previous auth.json to {backup}")
    print(f"Swapped active Codex account to '{row.get('label')}'")


def cmd_current(_args):
    current = active_auth()
    if not current:
        raise SystemExit(f"No valid active Codex auth found at {auth_path()}")

    store, _ = load_store(migrate=False)
    current_id = account_id(current)
    label = "-"
    for row in store.get("accounts") or []:
        if current_id and account_id(row.get("auth") or {}) == current_id:
            label = row.get("label") or "-"
            break

    print(f"LABEL       {label}")
    print(f"AUTH MODE   {current.get('auth_mode') or '-'}")
    print(f"REFRESHED   {current.get('last_refresh') or '-'}")


def cmd_relabel(_args):
    store, _ = load_store(migrate=False)
    changed = 0
    for row in store.get("accounts") or []:
        auth = row.get("auth") or {}
        label = infer_label(auth)
        if label and row.get("label") != label:
            print(f"{row.get('label') or '-'} -> {label}")
            row["label"] = label
            row["updated_at"] = now_iso()
            changed += 1
    if changed:
        backup = backup_file(accounts_path())
        save_store(store)
        if backup:
            print(f"Backed up previous accounts.json to {backup}")
    print(f"Relabeled {changed} account(s)")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="codex-account",
        description="Manage saved Codex auth tokens and manually swap ~/.codex/auth.json.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    list_cmd = subcommands.add_parser("list", help="List saved accounts without printing tokens")
    list_cmd.set_defaults(func=cmd_list)

    current_cmd = subcommands.add_parser("current", help="Show the active auth account")
    current_cmd.set_defaults(func=cmd_current)

    relabel_cmd = subcommands.add_parser("relabel", help="Set saved labels from token email claims")
    relabel_cmd.set_defaults(func=cmd_relabel)

    add_cmd = subcommands.add_parser("add", help="Add or update a saved account")
    add_cmd.add_argument("label", nargs="?", help="Friendly label for this account")
    add_cmd.add_argument(
        "--from",
        dest="source",
        default=str(auth_path()),
        help="Codex auth JSON source path, or '-' for stdin. Defaults to active auth.json",
    )
    add_cmd.set_defaults(func=cmd_add)

    use_cmd = subcommands.add_parser("use", help="Swap active auth.json to a saved account")
    use_cmd.add_argument("target", help="Saved account index, label, email, or account id fragment")
    use_cmd.set_defaults(func=cmd_use)

    return parser


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
