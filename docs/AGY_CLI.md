# AGY CLI Account Management

`agy` launches Antigravity normally and provides safe account-management commands when a management subcommand is used.

## Quick Start

```bash
agy doctor
agy account list
agy status
```

`agy status` reads cached quota data immediately. Run a live provider check only when needed:

```bash
agy status --refresh
```

## Account Commands

```bash
agy account list
agy account current
agy account add
agy account add --label personal
agy account use 2
agy account use personal
agy account rename 2 work
agy account remove 2 --yes
```

- `add` imports the currently authenticated Antigravity token and preserves the authenticated email.
- `--label` and `rename` change only the display label, not the stored email or OAuth token.
- Targets accept a 1-based index, email fragment, or display-label fragment.
- Removing the active account activates the first remaining account.
- Removal requires `--yes` and creates a backup first.

## Backup And Restore

Account mutations create timestamped backups under:

```text
~/.gemini/antigravity-cli/backups/
```

Manual backup and restore:

```bash
agy backup
agy backup --out ~/secure-backups/agy-accounts.json
agy restore ~/.gemini/antigravity-cli/backups/accounts-YYYYMMDD-HHMMSS.json --yes
agy restore --yes  # restores the newest timestamped backup
```

Before restore, the current state is backed up automatically. Backup files contain OAuth credentials and are created with user-only permissions (`0600`). Do not commit or share them.

## Doctor

```bash
agy doctor
agy --json doctor
```

Doctor checks whether `accounts.json` is present and valid, counts configured accounts and backups, verifies local token availability, and reports missing account tokens. It never prints credential values.

## JSON Output

Use `--json` before or after the command:

```bash
agy --json account list
agy account current --json
agy --json status
agy --json status --refresh
agy --json backup
```

JSON output contains account metadata, status, and boolean token availability only. Access tokens and refresh tokens are never emitted. Errors use:

```json
{"error": "description"}
```

## Compatibility Commands

Existing commands remain available:

| Existing command | Preferred command |
|---|---|
| `agy list` | `agy account list` |
| `agy current` | `agy account current` |
| `agy select 2` | `agy account use 2` |
| `agy add-current` | `agy account add` |
| `agy add-current-account` | `agy account add` |
| `agy remove-account 2 --yes` | `agy account remove 2 --yes` |
| `agy info` / `agy show` | `agy status --refresh` |

## Uninstall Safety

```bash
python3 install-agy.py --uninstall
```

Uninstall removes only installed wrappers and Python modules. It preserves `accounts.json`, `accounts-backup.json`, active tokens, backups, settings, logs, conversations, and caches. Credential deletion is never part of normal uninstall.
