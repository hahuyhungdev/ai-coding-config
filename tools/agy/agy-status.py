#!/usr/bin/env python3
import argparse
import contextlib
import difflib
import json
import os
import sys
from pathlib import Path

from accounts import (
    add_token_from_input,
    clean_conversations,
    delete_conversation,
    get_account_status,
    import_current_token,
    import_from_file,
    show_weekly_usage,
)
from storage import (
    active_account_index,
    backup_accounts,
    doctor_report,
    load_accounts,
    public_accounts,
    resolve_account,
    restore_accounts,
    write_accounts,
)
from switch import auto_switch_account, post_check_and_switch, rotate_account
from utils import AGY_DIR, TOKEN_FILE, sort_rows_by_remaining_quota


TOP_LEVEL_COMMANDS = [
    "status", "list", "ls", "accounts", "use", "select", "choose",
    "current", "rename", "remove", "rm", "add", "import", "save",
    "doctor", "backup", "restore", "weekly",
    "changelog", "install", "models", "plugin", "plugins", "update",
    "compact", "clean", "cleanup", "rotate",
]


def emit_json(payload):
    print(json.dumps(payload, indent=2))


def print_unknown_command(args):
    if not args:
        print("Unknown command.", file=sys.stderr)
        print("Run 'agy --help' to see available commands.", file=sys.stderr)
        return 2



    unknown = args[0]
    cutoff = 0.27 if len(unknown) == 1 else 0.5
    matches = difflib.get_close_matches(unknown, TOP_LEVEL_COMMANDS, n=1, cutoff=cutoff)
    print(f"Unknown command: {unknown}", file=sys.stderr)
    if matches:
        print("Did you mean:", file=sys.stderr)
        for match in matches:
            print(f"  agy {match}", file=sys.stderr)
    else:
        print("Run 'agy --help' to see available commands.", file=sys.stderr)
    return 2


def print_cached_status(rows):
    print("IDX  ACCOUNT                  STATUS       QUOTA             RESET TIME")
    for row in rows:
        active = " *" if row["active"] else ""
        print(
            f"{row['index']:<4} {row['display'] + active:<24} "
            f"{row['status']:<12} {row['quota']:<17} {row['reset_time']}"
        )
    print("Use 'agy status' for a live quota check.")


def account_list(json_output=False):
    rows = public_accounts(load_accounts())
    if json_output:
        emit_json({"accounts": rows})
    else:
        print_cached_status(rows)


def account_current(json_output=False):
    accounts = load_accounts()
    index = active_account_index(accounts)
    if index is None:
        raise ValueError("No active account found")
    row = public_accounts(accounts)[index]
    if json_output:
        emit_json({"account": row})
    else:
        print(f"Active account: {row['email']} ({row['display']}, index {row['index']})")


def account_use(target, json_output=False):
    accounts = load_accounts()
    index = resolve_account(accounts, target)
    selected = accounts[index]
    Path(TOKEN_FILE).write_text(json.dumps(selected, indent=2) + "\n", encoding="utf-8")
    os.chmod(TOKEN_FILE, 0o600)
    next_index = (index + 1) % len(accounts)
    Path(AGY_DIR, ".current_index").write_text(str(next_index), encoding="utf-8")
    row = public_accounts(accounts)[index]
    row["active"] = True
    if json_output:
        emit_json({"account": row})
    else:
        quota_str = f" - Quota: {row['quota']}"
        if row.get("reset_time"):
            quota_str += f" ({row['reset_time']})"
        print(f"Switched active account to {row['display']} ({row['email']}){quota_str}")


def account_rename(target, label, json_output=False):
    accounts = load_accounts()
    index = resolve_account(accounts, target)
    accounts[index]["label"] = label
    backup_path = write_accounts(accounts)
    row = public_accounts(accounts)[index]
    if json_output:
        emit_json({"account": row, "backup": backup_path})
    else:
        print(f"Renamed account {row['email']} to '{label}'")
        print(f"Backup: {backup_path}")


def account_remove(target, confirmed, json_output=False):
    if not confirmed:
        raise ValueError("Account removal requires --yes")
    accounts = load_accounts()
    index = resolve_account(accounts, target)
    active_index = active_account_index(accounts)
    removed = public_accounts(accounts)[index]
    accounts.pop(index)
    backup_path = write_accounts(accounts)
    if active_index == index:
        if accounts:
            Path(TOKEN_FILE).write_text(json.dumps(accounts[0], indent=2) + "\n", encoding="utf-8")
            os.chmod(TOKEN_FILE, 0o600)
        else:
            Path(TOKEN_FILE).unlink(missing_ok=True)
    Path(AGY_DIR, ".current_index").write_text("0", encoding="utf-8")
    if json_output:
        emit_json({"removed": removed, "backup": backup_path})
    else:
        print(f"Removed account {removed['display']} ({removed['email']})")
        print(f"Backup: {backup_path}")


def account_add(label, json_output=False):
    with contextlib.redirect_stdout(sys.stderr if json_output else sys.stdout):
        import_current_token(None)
    accounts = load_accounts()
    index = active_account_index(accounts)
    if label and index is not None:
        accounts[index]["label"] = label
        write_accounts(accounts)
    if json_output:
        row = public_accounts(accounts)[index if index is not None else len(accounts) - 1]
        emit_json({"account": row})


def run_status(refresh, json_output=False):
    if json_output:
        with contextlib.redirect_stdout(sys.stderr):
            get_account_status()
        emit_json({
            "accounts": sort_rows_by_remaining_quota(public_accounts(load_accounts())),
            "refreshed": True,
        })
    else:
        get_account_status()


def run_backup(output_path, json_output=False):
    path = backup_accounts(output_path)
    if not path:
        raise ValueError("accounts.json is missing")
    if json_output:
        emit_json({"path": path})
    else:
        print(f"Backup created: {path}")


def run_restore(path, confirmed, json_output=False):
    if not confirmed:
        raise ValueError("Restore requires --yes")
    restored_from, previous_backup = restore_accounts(path)
    payload = {"restored_from": restored_from, "previous_backup": previous_backup}
    if json_output:
        emit_json(payload)
    else:
        print(f"Accounts restored from: {restored_from}")
        print(f"Previous state backup: {previous_backup}")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="agy",
        description="Launch Antigravity and safely manage local accounts.",
        epilog="""
original agy subcommands:
  changelog           Show changelog and release notes
  help                Show help for subcommands
  install             Configure environment paths and shell settings
  models              List available models
  plugin (plugins)    Manage plugins (install, uninstall, list, enable, disable)
  update              Update CLI

Use 'agy help <command>' or 'agy <command> --help' for command-specific help.
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--json", action="store_true", help="Emit stable JSON without credential values")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="Run a live quota refresh")
    status.add_argument("--refresh", action="store_true", help="Accepted for compatibility; status refreshes by default")

    subparsers.add_parser("list", help="List accounts")
    add = subparsers.add_parser("add", help="Import the current authenticated account")
    add.add_argument("--label")
    subparsers.add_parser("current", help="Show the active account")
    use = subparsers.add_parser("use", help="Switch the active account")
    use.add_argument("target")
    rename = subparsers.add_parser("rename", help="Set a display label without changing email")
    rename.add_argument("target")
    rename.add_argument("label")
    remove = subparsers.add_parser("remove", help="Remove an account from the local pool")
    remove.add_argument("target")
    remove.add_argument("--yes", action="store_true", help="Confirm account removal")

    subparsers.add_parser("doctor", help="Check account files and token health")
    backup = subparsers.add_parser("backup", help="Back up accounts.json")
    backup.add_argument("--out")
    restore = subparsers.add_parser("restore", help="Restore an account backup")
    restore.add_argument("path", nargs="?")
    restore.add_argument("--yes", action="store_true", help="Confirm restore")
    subparsers.add_parser("weekly", help="Show local seven-day usage")

    return parser


def translate_legacy_args(args):
    if not args:
        return args
    aliases = {
        "list": ["list"],
        "ls": ["list"],
        "accounts": ["list"],
        "info": ["status", "--refresh"],
        "show": ["status", "--refresh"],
        "current": ["current"],
        "select": ["use"],
        "choose": ["use"],
        "use": ["use"],
        "add-current": ["add"],
        "add-current-account": ["add"],
        "import": ["add"],
        "save": ["add"],
        "remove-account": ["remove"],
        "rm-account": ["remove"],
        "delete-account": ["remove"],
        "week": ["weekly"],
        "usage-week": ["weekly"],
        "weekly-usage": ["weekly"],
        "compact": ["clean"],
    }
    if args[0] in ("help", "guide"):
        if len(args) > 1:
            return translate_legacy_args(args[1:]) + ["--help"]
        return ["--help"]
    if args[0] in aliases:
        return aliases[args[0]] + args[1:]
    return args


def run_legacy_internal(args):
    command = args[0] if args else ""
    if command == "rotate":
        rotate_account()
    elif command == "auto-switch":
        auto_switch_account()
    elif command == "post-check":
        post_check_and_switch()
    elif command in ("daemon", "auto"):
        from auto_rotate_daemon import main as daemon_main
        daemon_main()
    elif command in ("add-token", "paste", "new-token"):
        add_token_from_input(args[1] if len(args) > 1 else None)
    elif command in ("import-file", "add-file", "load"):
        if len(args) < 2:
            raise ValueError("Usage: agy import-file <path.json> [label]")
        import_from_file(args[1], args[2] if len(args) > 2 else None)
    elif command in ("clean", "cleanup", "prune", "compact"):
        clean_conversations()
    elif command in ("delete", "remove", "rm"):
        delete_conversation(args[1] if len(args) > 1 else None)
    else:
        return False
    return True


def main(argv=None):
    raw_args = list(sys.argv[1:] if argv is None else argv)
    if raw_args and raw_args[0] == "_suggest":
        return print_unknown_command(raw_args[1:])
    if "--json" in raw_args and raw_args[0] != "--json":
        raw_args.remove("--json")
        raw_args.insert(0, "--json")
    try:
        if run_legacy_internal(raw_args):
            return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    translated_args = translate_legacy_args(raw_args)
    args = build_parser().parse_args(translated_args)
    try:
        if args.command == "status":
            run_status(args.refresh, args.json)
        elif args.command == "list":
            account_list(args.json)
        elif args.command == "add":
            account_add(args.label, args.json)
        elif args.command == "current":
            account_current(args.json)
        elif args.command == "use":
            account_use(args.target, args.json)
        elif args.command == "rename":
            account_rename(args.target, args.label, args.json)
        elif args.command == "remove":
            account_remove(args.target, args.yes, args.json)
        elif args.command == "doctor":
            report = doctor_report()
            if args.json:
                emit_json(report)
            else:
                print("AGY account health: " + ("OK" if report["ok"] else "Needs attention"))
                print(f"Accounts: {report['account_count']}")
                print(f"Backups: {report['backup_count']}")
                for issue in report["issues"]:
                    print(f"- {issue}")
        elif args.command == "backup":
            run_backup(args.out, args.json)
        elif args.command == "restore":
            run_restore(args.path, args.yes, args.json)
        elif args.command == "weekly":
            show_weekly_usage()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        if getattr(args, "json", False):
            print(json.dumps({"error": str(exc)}))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
