# AGY CLI Account Management

`agy` launches Antigravity normally and provides safe account-management commands when a management subcommand is used.

## Quick Start

```bash
agy doctor
agy list
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

Nested command typos receive the same treatment, for example `agy lits` suggests `agy list`.

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
- **Custom wrapper commands** (e.g. `status`, `list`, `use`) will display the wrapper's account management help.
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
agy list
agy current
agy add
agy add --label personal
agy use 2
agy use personal
agy rename 2 work
agy remove 2 --yes
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
agy --json list
agy current --json
agy --json status
agy --json status --refresh
agy --json backup
```

JSON output contains account metadata, status, and boolean token availability only. Access tokens and refresh tokens are never emitted. Errors use:

```json
{"error": "description"}
```

## Compatibility Commands

Legacy commands are automatically translated to their preferred counterparts:

| Command | Action |
|---|---|
| `agy list` / `agy ls` / `agy accounts` | List all accounts |
| `agy current` | Show the active account |
| `agy use 2` / `agy select 2` / `agy choose 2` | Switch active account to index 2 |
| `agy add` / `agy import` / `agy save` | Import current active token |
| `agy remove 2 --yes` / `agy rm 2 --yes` | Remove account from pool |
| `agy clean` / `agy cleanup` / `agy prune` | Clean up automated or orphaned session logs |
| `agy info` / `agy show` | Live status check (runs `agy status`) |

## Quota Management & Auto-Switching

The `agy` CLI wrapper includes an automated, smart quota management system to handle rate-limits and usage caps across multiple accounts seamlessly.

### Background Daemon Monitoring (`agy auto` / `agy daemon`)
To monitor and automatically rotate accounts for subagents running in the background, you can launch the auto-rotate daemon:
```bash
agy auto
```
*(Note: `agy daemon` is also supported as an alias for compatibility).*

The daemon scans CLI logs (`log/cli-*.log`) and subagent transcripts (`brain/**/*.jsonl`) every 5 minutes (`--interval 300`) to immediately switch accounts upon detecting any `429` or `RESOURCE_EXHAUSTED` API errors.

### Auto-Switching Strategy (Round-Robin With Health Gate)
- When starting a session, the wrapper checks if the active account is blocked or running low on quota ($\le 30\%$).
- If a switch is needed, `agy` selects the next configured account in round-robin order, skipping accounts that are blocked or below the health threshold.
- If no healthy candidate exists, it falls back to the non-blocked low-quota candidate with the best remaining quota as a last-resort continuation path.
- The next-index marker is stored in `~/.gemini/antigravity-cli/.current_index`.
- To restore the previous highest-quota behavior, set `"rotationPolicy": "highest-quota"` in `~/.gemini/antigravity-cli/settings.json`. The default is `"round-robin"`.

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

## Troubleshooting & Recent Bug Fixes

A comprehensive QA audit was conducted on 2026-06-27 to evaluate edge cases, error handling, and concurrency issues in the custom account manager. The following fixes were implemented:

1. **Empty Configuration Crash**: Fixed a crash (`JSONDecodeError`) that occurred when `accounts.json`, `settings.json`, or `.current_index` were empty (0-byte files). They now gracefully default to empty pools (`[]`) or default policies (`round-robin`).
2. **Active Token Sync Protection**: Implemented `sync_active_token_to_accounts()` to ensure that when `agy-bin` refreshes the active session token, the updated token is saved back to `accounts.json` before any account rotation occurs. This prevents losing refreshed tokens when switching accounts.
3. **Duplicate Token Rotation Gate**: Enhanced `select_replacement_index()` to detect and filter out duplicate entries (accounts using the same refresh token), preventing endless switch-loops on the same blocked credentials.
4. **Daemon Concurrency Lock**: Added process-level locking using `fcntl.flock` on `auto_rotate_daemon.lock` to prevent multiple background auto-rotate daemons from running concurrently and stepping on each other.
5. **Path Leak Fix for Sandboxing**: Resolved an issue in `generate_quota_rollover()` where it was bypassing sandbox environments and accessing `~/.gemini/antigravity-cli/brain` directly instead of respecting `AGY_DIR_OVERRIDE`.
6. **Robust Model Quota Formatting**: Updated `_quota_summary` to gracefully fall back and extract quota percentages/resets from *any* available models in the output if the hardcoded default model types (like `Gemini 3.5 Flash (Medium)`) are not returned or present in the current user settings.
7. **Clean Commands Integration**: Promoted `clean`, `cleanup`, and `prune` to first-class CLI commands with proper `--help` and `--json` support (returning structured execution status).
8. **Wrapper Routing Conflicts**: Fixed routing in `tools/agy/agy` where `rename` was incorrectly routed as a typo (unknown command), and `remove`/`rm` were incorrectly intercepted as conversation deletes instead of account removal.
9. **Generic Flag Positioning**: Fixed translation issues where placing `--json` first (e.g. `agy --json rm`) bypassed command aliases. `--json` is now processed generically before translating other arguments.
10. **Multi-Terminal Daemon Kill Bug**: Running `agy auto` in Terminal 2 previously used `pkill -f 'auto_rotate_daemon.py'` which killed Terminal 1's daemon, leaving it unmonitored. Replaced with PID file-based liveness checking: Terminal 2 now detects and reuses the existing daemon. The daemon writes a PID file on startup and cleans it up on SIGTERM/exit.
11. **Double Error Message on Missing Args**: Commands like `agy rename 1` (without the label) produced argparse's error *plus* a confusing "Unknown command: rename / Did you mean: agy rename" suggestion. The `SystemExit` handler now checks whether the subcommand is a valid registered command and suppresses the duplicate suggestion.
