#!/usr/bin/env python3
import argparse
import base64
import getpass
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_THRESHOLD_USED_PERCENT = 70.0
DEFAULT_LIVE_CHECK_TIMEOUT_SECONDS = 90.0
DEFAULT_LIVE_CHECK_PROMPT = "Reply exactly OK."


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


def codex_bin_path():
    return Path(os.environ.get("CODEX_REAL_BIN", Path.home() / ".local/bin/codex-bin")).expanduser()


def sandbox_parent():
    path = codex_home() / "tmp"
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def sandbox_tempdir(prefix):
    return tempfile.TemporaryDirectory(
        prefix=prefix,
        dir=str(sandbox_parent()),
        ignore_cleanup_errors=True,
    )


def live_check_timeout(value=None):
    value = value if value is not None else os.environ.get("CODEX_ACCOUNT_STATUS_TIMEOUT")
    if not value:
        return DEFAULT_LIVE_CHECK_TIMEOUT_SECONDS
    try:
        timeout = float(value)
    except ValueError as exc:
        raise SystemExit(f"CODEX_ACCOUNT_STATUS_TIMEOUT must be a number, got {value!r}") from exc
    if timeout <= 0:
        raise SystemExit("CODEX_ACCOUNT_STATUS_TIMEOUT must be greater than 0")
    return timeout


def live_check_prompt():
    return os.environ.get("CODEX_ACCOUNT_STATUS_PROMPT", DEFAULT_LIVE_CHECK_PROMPT)


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


def format_remaining_rate_window(window):
    if not isinstance(window, dict):
        return "?"
    used = window.get("used_percent")
    if used is None:
        return "?"
    try:
        remaining = max(0.0, min(100.0, 100.0 - float(used)))
        return f"{int(round(remaining))}%"
    except (TypeError, ValueError):
        return "?"


def rate_window_used_percent(window):
    if not isinstance(window, dict):
        return None
    used = window.get("used_percent")
    if used is None:
        return None
    try:
        return float(used)
    except (TypeError, ValueError):
        return None


def normalize_percent(value):
    if value is None:
        return None
    return int(value) if float(value).is_integer() else round(float(value), 2)


def compact_message(value, limit=96):
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def effective_used_percent(rate_limits):
    if not isinstance(rate_limits, dict):
        return None
    windows = [
        rate_window_used_percent(rate_limits.get("primary")),
        rate_window_used_percent(rate_limits.get("secondary")),
    ]
    windows = [value for value in windows if value is not None]
    if not windows:
        return None
    return max(windows)


def format_quota(rate_limits):
    if not isinstance(rate_limits, dict):
        return "?"
    primary = format_remaining_rate_window(rate_limits.get("primary"))
    secondary = format_remaining_rate_window(rate_limits.get("secondary"))
    if primary == "?" and secondary == "?":
        credits = rate_limits.get("credits") or {}
        balance = credits.get("balance")
        return f"credits:{balance}" if balance not in (None, "") else "?"
    return f"5H:{primary}/W:{secondary}"


def format_usage(rate_limits):
    if not isinstance(rate_limits, dict):
        return "?"
    primary = format_rate_window(rate_limits.get("primary"))
    secondary = format_rate_window(rate_limits.get("secondary"))
    if primary == "?" and secondary == "?":
        return "?"
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


def latest_rate_limits_by_plan(base=None):
    base = Path(base).expanduser() if base is not None else sessions_dir()
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


def snapshot_from_row(row):
    snapshot = row.get("rate_limits_snapshot")
    if not isinstance(snapshot, dict):
        return None
    rate_limits = snapshot.get("rate_limits")
    if not has_quota_windows(rate_limits):
        return None
    timestamp = parse_timestamp(snapshot.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc)
    return {"timestamp": timestamp, "rate_limits": rate_limits}


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


def inferred_identity_label(auth_blob):
    email = account_email(auth_blob)
    if email:
        return email
    name = account_name(auth_blob)
    if name:
        return name
    account = account_id(auth_blob)
    if account:
        return account[:8]
    return ""


def timestamped_label(prefix):
    return f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


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


def account_snapshot(row, auth, active, current_plan, latest_by_plan, latest_any):
    plan = account_plan(auth) or "-"
    quota_snapshot = snapshot_from_row(row)
    if not quota_snapshot:
        quota_snapshot = latest_by_plan.get(plan)
    if active and (not quota_snapshot) and latest_any:
        latest_plan = latest_any["rate_limits"].get("plan_type")
        if latest_plan in (None, "unknown", current_plan):
            quota_snapshot = latest_any
    return plan, quota_snapshot


def account_status_from_usage(used_percent, threshold_used):
    if used_percent is None:
        return "unknown", False
    if used_percent >= threshold_used:
        return "low", False
    return "healthy", True


def build_account_records(threshold_used=DEFAULT_THRESHOLD_USED_PERCENT):
    store, _ = load_store(migrate=False)
    current = active_auth()
    current_id = account_id(current) if current else ""
    current_plan = account_plan(current) if current else ""
    latest_by_plan, latest_any = latest_rate_limits_by_plan()

    records = []
    for index, row in enumerate(store.get("accounts") or [], start=1):
        auth = row.get("auth") or {}
        acc_id = account_id(auth)
        active = bool(acc_id and acc_id == current_id)
        plan, quota_snapshot = account_snapshot(row, auth, active, current_plan, latest_by_plan, latest_any)
        rate_limits = quota_snapshot["rate_limits"] if quota_snapshot else None
        used_percent = effective_used_percent(rate_limits)
        status, healthy = account_status_from_usage(used_percent, threshold_used)
        records.append({
            "index": index,
            "active": active,
            "label": row.get("label") or "-",
            "plan": plan,
            "quota": format_quota(rate_limits) if rate_limits else "?",
            "usage": format_usage(rate_limits) if rate_limits else "?",
            "reset_time": format_reset_time(rate_limits) if rate_limits else "?",
            "used_percent": normalize_percent(used_percent),
            "status": status,
            "healthy": healthy,
            "_auth": auth,
        })
    return records


def public_account_record(record):
    return {key: value for key, value in record.items() if not key.startswith("_")}


def snapshot_payload(snapshot):
    return {
        "timestamp": snapshot["timestamp"].isoformat(),
        "rate_limits": snapshot["rate_limits"],
        "source": "codex_exec_sandbox",
    }


def first_error_message(value):
    if isinstance(value, dict):
        for key in ("message", "error", "reason", "detail", "code"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return item.strip()
            nested = first_error_message(item)
            if nested:
                return nested
        for item in value.values():
            nested = first_error_message(item)
            if nested:
                return nested
    if isinstance(value, list):
        for item in value:
            nested = first_error_message(item)
            if nested:
                return nested
    return None


def error_message_from_json_key_line(line):
    for key in ("message", "error", "reason", "detail", "code"):
        prefix = f'"{key}":'
        if not line.startswith(prefix):
            continue
        raw_value = line.split(":", 1)[1].strip().rstrip(",")
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            return raw_value.strip('"')
        if isinstance(parsed, str) and parsed.strip():
            return parsed.strip()
        return first_error_message(parsed)
    return None


def is_generic_codex_notice(message):
    return (message or "").strip() in {
        "Reading additional input from stdin...",
    }


def process_error_detail(completed):
    for text in (completed.stderr, completed.stdout):
        text = (text or "").strip()
        if not text:
            continue
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if parsed is not None:
            message = first_error_message(parsed)
            if message and not is_generic_codex_notice(message):
                return message[:300]
        for line in reversed(text.splitlines()):
            line = line.strip()
            if not line or line in ("{", "}", "[", "]"):
                continue
            if is_generic_codex_notice(line):
                continue
            key_line_message = error_message_from_json_key_line(line)
            if key_line_message and not is_generic_codex_notice(key_line_message):
                return key_line_message[:300]
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                return line[:300]
            message = first_error_message(parsed)
            if message and not is_generic_codex_notice(message):
                return message[:300]
    return ""


def select_sandbox_snapshot(auth, sandbox_codex_home):
    latest_by_plan, latest_any = latest_rate_limits_by_plan(sandbox_codex_home / "sessions")
    plan = account_plan(auth)
    if plan and latest_by_plan.get(plan):
        return latest_by_plan[plan]
    return latest_any


def refresh_account_rate_limits(row, timeout=None):
    label = row.get("label") or "-"
    auth = row.get("auth") or {}
    try:
        auth = validate_auth_blob(auth, f"account {label}")
    except SystemExit as exc:
        return None, str(exc)

    binary = codex_bin_path()
    with sandbox_tempdir("codex-account-status-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        sandbox_codex_home = tmp_path / ".codex"
        write_private_json(sandbox_codex_home / "auth.json", auth)

        env = os.environ.copy()
        env["CODEX_HOME"] = str(sandbox_codex_home)
        env["CODEX_ACCOUNT_LABEL"] = str(label)
        for key in ("CODEX_AUTH_FILE", "CODEX_ACCOUNTS_FILE", "CODEX_SESSIONS_DIR"):
            env.pop(key, None)

        command = [
            str(binary),
            "exec",
            "--json",
            "--ignore-rules",
            "--ignore-user-config",
            "--skip-git-repo-check",
            "-C",
            str(tmp_path),
            live_check_prompt(),
        ]
        timeout_seconds = live_check_timeout(timeout)
        try:
            completed = subprocess.run(
                command,
                env=env,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except FileNotFoundError:
            return None, f"Codex binary not found at {binary}"
        except subprocess.TimeoutExpired:
            return None, f"Codex live status timed out after {normalize_percent(timeout_seconds)}s"

        snapshot = select_sandbox_snapshot(auth, sandbox_codex_home)
        if snapshot:
            refreshed_auth = load_json(sandbox_codex_home / "auth.json")
            if is_auth_blob(refreshed_auth) and (
                not account_id(auth) or account_id(refreshed_auth) == account_id(auth)
            ):
                row["auth"] = refreshed_auth
            return snapshot, None

        error_detail = process_error_detail(completed)
        detail = f": {error_detail}" if error_detail else ""
        if completed.returncode:
            return None, f"Codex exec exited {completed.returncode} without rate limits{detail}"
        return None, f"Codex exec completed without rate limits{detail}"


def refresh_store_rate_limits(store, target=None, timeout=None, progress=False):
    refreshed_count = 0
    errors = []
    refreshed_at = now_iso()
    if target:
        _, row = find_account(store, target)
        rows = [row]
    else:
        rows = store.get("accounts") or []
    total = len(rows)
    for position, row in enumerate(rows, start=1):
        label = row.get("label") or "-"
        if progress:
            print(f"Refreshing Codex account {position}/{total}: {label}", file=sys.stderr, flush=True)
        try:
            snapshot, error = refresh_account_rate_limits(row, timeout=timeout)
        except Exception as exc:
            snapshot, error = None, str(exc)
        if snapshot:
            row["rate_limits_snapshot"] = snapshot_payload(snapshot)
            row["last_rate_limit_refresh"] = refreshed_at
            row["updated_at"] = refreshed_at
            refreshed_count += 1
        if error:
            errors.append({"label": label, "error": error})
    if refreshed_count:
        save_store(store)
    return refreshed_count, errors


def emit_json(payload):
    print(json.dumps(payload, indent=2))


def cmd_list(_args):
    print("IDX  A  LABEL                          LEFT           RESET")
    for record in build_account_records():
        active = "*" if record["active"] else ""
        print(
            f"{record['index']:<4} {active:<2} {record['label']:<30} "
            f"{record['quota']:<14} {record['reset_time']}"
        )


def cmd_status(args):
    refreshed_count = 0
    refresh_errors = []
    should_refresh = not args.no_refresh
    if should_refresh:
        auth_file = auth_path()
        original_auth = None
        auth_existed = auth_file.exists()
        if auth_existed:
            try:
                original_auth = auth_file.read_bytes()
            except OSError:
                original_auth = None
        try:
            store, _ = load_store(migrate=False)
            refreshed_count, refresh_errors = refresh_store_rate_limits(
                store,
                target=args.account,
                timeout=args.timeout,
                progress=True,
            )
        finally:
            if original_auth is not None:
                current_auth = None
                try:
                    current_auth = auth_file.read_bytes()
                except OSError:
                    pass
                if current_auth != original_auth:
                    auth_file.parent.mkdir(parents=True, exist_ok=True)
                    auth_file.write_bytes(original_auth)
                    os.chmod(auth_file, 0o600)
            elif not auth_existed:
                try:
                    auth_file.unlink()
                except FileNotFoundError:
                    pass

    payload = status_payload(
        threshold_used=args.threshold_used,
        refreshed=should_refresh,
        refresh_target=args.account if should_refresh else None,
        refresh_count=refreshed_count,
        refresh_errors=refresh_errors,
    )
    if args.json:
        emit_json(payload)
        return

    print_status_text(payload)


def choose_rotation_target(records, force=False, allow_unknown=False):
    active = next((record for record in records if record["active"]), None)
    candidates = [record for record in records if not record["active"]]
    if not candidates:
        return active, None, "No alternate Codex accounts are saved"

    if active and active["healthy"] and not force:
        return active, None, "Active Codex account is healthy; use --force to rotate anyway"

    known = [record for record in candidates if record["used_percent"] is not None]
    healthy_known = [record for record in known if record["healthy"]]
    if healthy_known:
        target = min(healthy_known, key=lambda record: (record["used_percent"], record["index"]))
        return active, target, "Selected saved account with lowest known cached usage"

    if known:
        target = min(known, key=lambda record: (record["used_percent"], record["index"]))
        return active, target, "No healthy candidate found; selected lowest known cached usage"

    if allow_unknown:
        return active, candidates[0], "Selected first unknown-usage account because --allow-unknown was set"

    return active, None, "No alternate Codex account has cached usage data; rerun after using another account or pass --allow-unknown"


def cmd_rotate(args):
    records = build_account_records(threshold_used=args.threshold_used)
    active, target, reason = choose_rotation_target(
        records,
        force=args.force,
        allow_unknown=args.allow_unknown,
    )
    dry_run = args.dry_run
    switched = False
    backup = None

    if target and not dry_run:
        auth = validate_auth_blob(target["_auth"], f"account {target['label']}")
        backup_path = backup_file(auth_path())
        write_private_json(auth_path(), auth)
        backup = str(backup_path) if backup_path else None
        switched = True

    payload = {
        "switched": switched,
        "would_switch": bool(target),
        "dry_run": dry_run,
        "reason": reason,
        "active": public_account_record(active) if active else None,
        "target": public_account_record(target) if target else None,
    }
    if backup:
        payload["backup"] = backup

    if args.json:
        emit_json(payload)
        return

    if target:
        action = "Would switch" if dry_run else "Switched"
        print(f"{action} Codex account to '{target['label']}' ({target['quota']})")
    else:
        print("No Codex account rotation performed.")
    print(reason)
    if switched:
        print("The new account is written to disk. Restart Codex or compact the session to use it here.")


def read_auth_source(path_text):
    if path_text == "-":
        return validate_auth_blob(json.load(sys.stdin), "stdin")
    path = Path(path_text).expanduser()
    return validate_auth_blob(load_json(path), str(path))


def upsert_account(auth, label):
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
    return action, backup


def cmd_add(args):
    auth = read_auth_source(args.source)
    label = args.label or infer_label(auth)
    action, backup = upsert_account(auth, label)
    if backup:
        print(f"Backed up previous accounts.json to {backup}")
    print(f"{action} Codex account '{label}'")


def auth_from_refresh_token(token):
    return {
        "auth_mode": "chatgpt",
        "OPENAI_API_KEY": None,
        "tokens": {
            "refresh_token": token,
        },
        "last_refresh": now_iso(),
    }


def auth_from_token_text(text, source):
    text = (text or "").strip()
    if not text:
        raise SystemExit(f"No refresh token provided from {source}")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None

    if is_auth_blob(payload):
        return validate_auth_blob(payload, source)

    if isinstance(payload, dict):
        tokens = payload.get("tokens") if isinstance(payload.get("tokens"), dict) else payload
        token = tokens.get("refresh_token") or tokens.get("refreshToken")
        if not token:
            raise SystemExit(f"{source} JSON does not include refresh_token")
        return auth_from_refresh_token(str(token).strip())

    if isinstance(payload, str):
        text = payload.strip()

    if text.lower().startswith("bearer "):
        text = text[7:].strip()
    if not text:
        raise SystemExit(f"No refresh token provided from {source}")
    return auth_from_refresh_token(text)


def read_token_source(path_text):
    if path_text == "-":
        if sys.stdin.isatty():
            text = getpass.getpass("Paste Codex refresh token: ")
        else:
            text = sys.stdin.read()
        return auth_from_token_text(text, "stdin")
    path = Path(path_text).expanduser()
    return auth_from_token_text(path.read_text(encoding="utf-8"), str(path))


def cmd_add_token(args):
    auth = read_token_source(args.source)
    label = args.label or inferred_identity_label(auth) or timestamped_label("pasted-token")
    action, backup = upsert_account(auth, label)
    if backup:
        print(f"Backed up previous accounts.json to {backup}")
    print(f"{action} Codex account '{label}' from refresh token")


def is_usage_limit_error(message):
    text = str(message or "").lower()
    return "usage limit" in text or "hit your usage limit" in text


def annotate_refresh_errors(records, refresh_errors):
    errors_by_label = {
        str(error.get("label") or ""): str(error.get("error") or "")
        for error in (refresh_errors or [])
        if error.get("label")
    }
    for record in records:
        error = errors_by_label.get(str(record.get("label") or ""))
        if not error:
            continue
        record["stale"] = True
        record["refresh_error"] = error
        record["healthy"] = False
        record["reset_time"] = "?"
        if is_usage_limit_error(error):
            record["status"] = "exhausted"
            record["quota"] = "0%"
            record["usage"] = "limit"
            record["used_percent"] = 100
        else:
            record["status"] = "stale"
            record["quota"] = "stale"
            record["usage"] = "stale"
            record["used_percent"] = None


def status_payload(threshold_used, refreshed=False, refresh_target=None, refresh_count=0, refresh_errors=None):
    records = build_account_records(threshold_used=threshold_used)
    public_records = [public_account_record(record) for record in records]
    annotate_refresh_errors(public_records, refresh_errors)
    active = next((record for record in public_records if record["active"]), None)
    return {
        "active": active,
        "accounts": public_records,
        "threshold_used_percent": normalize_percent(threshold_used),
        "source": "live_codex_exec_rate_limits" if refreshed else "cached_codex_session_rate_limits",
        "refreshed": bool(refreshed),
        "refresh_target": refresh_target,
        "refresh_count": refresh_count,
        "refresh_errors": refresh_errors or [],
    }


def print_status_text(payload):
    active = payload["active"]
    if active:
        print(
            f"Active: {active['label']} | {active['status']} | "
            f"left {active['quota']} | used {active['usage']} | reset {active['reset_time']}"
        )
    else:
        print(f"No active saved Codex account found at {auth_path()}")
    if payload["refreshed"]:
        print(f"Refreshed: {payload['refresh_count']} account(s)")
        for error in payload["refresh_errors"]:
            print(f"Warning: {error['label']}: {compact_message(error['error'])}")
    print("")
    print("IDX  A  LABEL                          STATUS    LEFT           USED           RESET")
    for record in payload["accounts"]:
        active_mark = "*" if record["active"] else ""
        print(
            f"{record['index']:<4} {active_mark:<2} {record['label']:<30} "
            f"{record['status']:<9} {record['quota']:<14} "
            f"{record['usage']:<14} {record['reset_time']}"
        )


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


def cmd_guide(_args):
    print("""Codex account quick guide

Daily commands:
  codex ls                         List saved accounts
  codex check [account]            Live-check all accounts, or one account if provided
  codex rotate --dry-run           Preview automatic switch
  codex rotate                     Switch when current account is low

Add accounts:
  codex token [label]              Paste a refresh token safely
  codex login-temp [label]         Browser/URL login in temporary CODEX_HOME
  codex login-temp --device-auth   Use device-code login when needed
  codex add <label>                Save the current active auth.json

Manual control:
  codex switch <account>           Swap active auth.json to a saved account
  codex current                    Show active account

Advanced commands stay available under:
  codex account ...
""")


def cmd_login_temp(args):
    with sandbox_tempdir("codex-account-login-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        sandbox_codex_home = tmp_path / ".codex"
        sandbox_codex_home.mkdir(parents=True, exist_ok=True)
        os.chmod(sandbox_codex_home, 0o700)
        env = os.environ.copy()
        env["CODEX_HOME"] = str(sandbox_codex_home)
        for key in ("CODEX_AUTH_FILE", "CODEX_ACCOUNTS_FILE", "CODEX_SESSIONS_DIR"):
            env.pop(key, None)

        login_command = [str(codex_bin_path()), "login"]
        if args.device_auth:
            login_command.append("--device-auth")

        completed = subprocess.run(
            login_command,
            env=env,
            check=False,
        )
        if completed.returncode:
            raise SystemExit(f"Temporary Codex login failed with exit code {completed.returncode}")

        sandbox_auth = sandbox_codex_home / "auth.json"
        auth = validate_auth_blob(load_json(sandbox_auth), str(sandbox_auth))
        label = args.label or inferred_identity_label(auth) or timestamped_label("login-temp")
        action, backup = upsert_account(auth, label)
        if backup and not args.json:
            print(f"Backed up previous accounts.json to {backup}")
        if not args.json:
            print(f"{action} Codex account '{label}' from temporary login")

    refreshed_count = 0
    refresh_errors = []
    if not args.no_refresh:
        store, _ = load_store(migrate=False)
        refreshed_count, refresh_errors = refresh_store_rate_limits(
            store,
            target=label,
            timeout=args.timeout,
            progress=True,
        )

    payload = status_payload(
        threshold_used=args.threshold_used,
        refreshed=not args.no_refresh,
        refresh_target=label if not args.no_refresh else None,
        refresh_count=refreshed_count,
        refresh_errors=refresh_errors,
    )
    if args.json:
        emit_json(payload)
    else:
        print_status_text(payload)


def build_parser():
    parser = argparse.ArgumentParser(
        prog=os.environ.get("CODEX_ACCOUNT_PROG", "codex-account"),
        description="Manage saved Codex auth tokens and manually swap ~/.codex/auth.json.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    list_cmd = subcommands.add_parser("list", help="List saved accounts without printing tokens")
    list_cmd.set_defaults(func=cmd_list)

    guide_cmd = subcommands.add_parser("guide", help="Print the short Codex account workflow guide")
    guide_cmd.set_defaults(func=cmd_guide)

    status_cmd = subcommands.add_parser("status", help="Live-refresh and show Codex account usage health")
    status_cmd.add_argument("--json", action="store_true", help="Emit stable JSON without credential values")
    status_cmd.add_argument(
        "--refresh",
        action="store_true",
        help="Accepted for compatibility; status refreshes by default",
    )
    status_cmd.add_argument(
        "--no-refresh",
        action="store_true",
        help="Use cached local usage snapshots without running a live Codex check",
    )
    status_cmd.add_argument(
        "--account",
        help="When refreshing, only check the saved account matching this index, label, email, or account id fragment",
    )
    status_cmd.add_argument(
        "--timeout",
        type=float,
        help="Per-account live check timeout in seconds. Defaults to CODEX_ACCOUNT_STATUS_TIMEOUT or 90.",
    )
    status_cmd.add_argument(
        "--threshold-used",
        type=float,
        default=DEFAULT_THRESHOLD_USED_PERCENT,
        help="Mark accounts as low when cached usage is at or above this percent",
    )
    status_cmd.set_defaults(func=cmd_status)

    rotate_cmd = subcommands.add_parser("rotate", help="Switch to the healthiest saved Codex account")
    rotate_cmd.add_argument("--dry-run", action="store_true", help="Show the selected account without changing auth.json")
    rotate_cmd.add_argument("--json", action="store_true", help="Emit stable JSON without credential values")
    rotate_cmd.add_argument(
        "--threshold-used",
        type=float,
        default=DEFAULT_THRESHOLD_USED_PERCENT,
        help="Treat accounts below this cached usage percent as healthy",
    )
    rotate_cmd.add_argument(
        "--allow-unknown",
        action="store_true",
        help="Allow rotation to an account without cached usage data when no known candidate exists",
    )
    rotate_cmd.add_argument(
        "--force",
        action="store_true",
        help="Rotate even when the active account is currently healthy",
    )
    rotate_cmd.set_defaults(func=cmd_rotate)

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

    add_token_cmd = subcommands.add_parser("add-token", help="Add or update a saved account from a pasted refresh token")
    add_token_cmd.add_argument("label", nargs="?", help="Friendly label for this account")
    add_token_cmd.add_argument(
        "--from",
        dest="source",
        default="-",
        help="Refresh token source path, or '-' for stdin/prompt. Defaults to stdin/prompt",
    )
    add_token_cmd.set_defaults(func=cmd_add_token)

    login_temp_cmd = subcommands.add_parser("login-temp", help="Login in a temporary CODEX_HOME and save that account")
    login_temp_cmd.add_argument("label", nargs="?", help="Friendly label for this account")
    login_temp_cmd.add_argument("--json", action="store_true", help="Emit status JSON after login")
    login_temp_cmd.add_argument("--no-refresh", action="store_true", help="Save the account without running a live quota check")
    login_temp_cmd.add_argument(
        "--device-auth",
        action="store_true",
        help="Use Codex device-code login instead of the default browser/URL login flow",
    )
    login_temp_cmd.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Per-account live check timeout in seconds after login. Defaults to 30.",
    )
    login_temp_cmd.add_argument(
        "--threshold-used",
        type=float,
        default=DEFAULT_THRESHOLD_USED_PERCENT,
        help="Mark accounts as low when usage is at or above this percent",
    )
    login_temp_cmd.set_defaults(func=cmd_login_temp)

    use_cmd = subcommands.add_parser("use", help="Swap active auth.json to a saved account")
    use_cmd.add_argument("target", help="Saved account index, label, email, or account id fragment")
    use_cmd.set_defaults(func=cmd_use)

    return parser


def main():
    try:
        args = build_parser().parse_args()
        args.func(args)
    except KeyboardInterrupt:
        print("Interrupted Codex account command", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
