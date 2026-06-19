# AGY CLI Account Management

`agy` launches Antigravity normally and provides safe account-management commands when a management subcommand is used.

## Quick Start

```bash
agy doctor
agy account list
agy status
```

Run `agy` with no arguments to open the interactive Antigravity CLI. Use its normal flags for direct prompts:

```bash
agy -p "summarize this project"
agy --model "Gemini 3.5 Flash (High)"
```

Unknown bare words are treated as command typos and never launch the AI CLI:

```text
$ agy s
Unknown command: s
Did you mean:
  agy status
```

Nested account-command typos receive the same treatment, for example `agy account lits` suggests `agy account list`.

Native Antigravity commands still pass directly to the original binary:

```bash
agy changelog
agy models
agy plugin list
agy update
agy help models
```

### Command Help Integration

Help commands are unified. You can run `agy help <command>` or `agy <command> --help` for any command:
- **Custom wrapper commands** (e.g. `status`, `account`) will display the wrapper's account management help.
- **Original native commands** (e.g. `models`, `plugin`) will automatically forward the help request to the original binary.

To see all custom and native subcommands in a single unified list, run:
```bash
agy --help
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

## Quota Management & Auto-Switching

The `agy` CLI wrapper includes an automated, smart quota management system to handle rate-limits and usage caps across multiple accounts seamlessly.

### Auto-Switching Strategy (Highest Quota First)
- When starting a session, the wrapper checks if the active account is blocked or running low on quota ($\le 30\%$).
- If a switch is needed, `agy` evaluates all configured accounts and selects the **healthy candidate with the highest remaining quota** (parsed from `agy status`). This avoids selecting nearly exhausted accounts.
- If all accounts are depleted, it attempts a same-account model fallback (e.g. falling back from Gemini to Claude) before prompting.

### Real-Time Session Rescue (Quota Rollover)
If a quota/rate-limit error occurs *during* an active interactive session:
1. The session exits with an error. The wrapper immediately triggers a `post-check` recovery.
2. It parses the newest log file (modified in the last 15 minutes) to identify the quota error, block duration, and active model.
3. **Context Recovery**: The script reads the interrupted session's `transcript.jsonl` from the brain cache and extracts the **last 6 turns (3 full exchanges)** of conversation history.
4. **Auto-Resume**: The wrapper switches to the highest-quota account and restarts the session, pre-loading the extracted conversation history under an automatic rollover prompt. This allows you to continue working seamlessly without losing your active context.

### Safe Block Expirations
- Accounts marked as `"🔴 Blocked"` are assigned a `blocked_until` ISO timestamp based on the API's reset time parsed from the logs.
- If the logs do not specify a reset time, the account is temporarily blocked for a **safe default of 2 hours**, after which it automatically becomes eligible for selection again.

## Uninstall Safety

```bash
python3 install-agy.py --uninstall
```

Uninstall removes only installed wrappers and Python modules. It preserves `accounts.json`, `accounts-backup.json`, active tokens, backups, settings, logs, conversations, and caches. Credential deletion is never part of normal uninstall.
