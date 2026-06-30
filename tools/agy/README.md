# Antigravity CLI Wrapper

`tools/agy` contains the installable `agy` wrapper and Python management CLI for the local Antigravity CLI runtime.

The installed runtime lives outside this repo at:

- `~/.local/bin/agy`: shell wrapper users run.
- `~/.gemini/antigravity-cli/agy-status.py`: Python command router.
- `~/.gemini/antigravity-cli/accounts.json`: local account pool and cached quota data.
- `~/.gemini/antigravity-cli/antigravity-oauth-token`: active account token used by the real Antigravity CLI.
- `~/.local/bin/agy-bin`: real upstream Antigravity binary.

## Command Flow

1. User runs `agy ...`.
2. `agy` shell wrapper decides whether the command is management or native Antigravity.
3. Management commands execute `agy-status.py`.
4. Prompt-mode commands run `auto-switch` first, then launch `agy-bin`.
5. If quota fails, the wrapper asks `post-check` whether to switch model or account, then retries.

## Module Map

- `agy`: shell entrypoint and retry/model-injection wrapper.
- `agy-status.py`: argparse router for management commands and legacy aliases.
- `accounts.py`: compatibility facade that re-exports the public command handlers.
- `account_commands.py`: cached account listing, weekly usage display, and legacy account select/remove helpers.
- `status_refresh.py`: live quota refresh, duplicate-token detection, token restoration, and status table updates.
- `token_import.py`: token import flows from the active token file, pasted JSON, and token JSON files.
- `conversation_commands.py`: local conversation/session cleanup and delete helpers.
- `switch.py`: model fallback and account rotation policy. Current policy is Gemini High first, Claude Opus second, then account rotation.
- `parser.py`: parsers for Antigravity quota screens and local log-derived usage signals.
- `pty_client.py`: pseudo-terminal runner used to query live quota screens.
- `storage.py`: account file loading, backups, public redaction, restore, token normalization, and token upsert helpers.
- `presentation.py`: terminal table rendering and active-account display helpers.
- `utils.py`: constants and small shared formatting/parsing helpers.

## Important Behavior

- `agy status` is the live quota refresh path. It may update `accounts.json` with fresh quota, refreshed token values, and `blocked_until`.
- `agy account list` is the fast cached path. It should not call the PTY or mutate account quota state.
- Live status output is sorted by effective remaining quota, but account indexes stay tied to the original account order.
- Duplicate refresh tokens are not independent accounts; live refresh marks later duplicates as `Dup`.
- Weekly usage is a local estimate from CLI logs, not an official provider billing/quota API.

### Notable Features & Account Rotation

### 1. Health-Gated Rotation Algorithm
Default account rotation mechanisms—including manual command `agy rotate`, the `/rotate` slash command, and CLI hook-based checks—use a unified **health gate** algorithm:
- **Ratio-Based Independent Thresholds**: The active account's health is evaluated independently against two distinct thresholds:
  - `threshold_5h` (defaults to 15%): The minimum remaining quota for the 5-Hour Session Limit.
  - `threshold_weekly` (defaults to 10%): The minimum remaining quota for the Weekly Limit.
  - **Low-Quota Condition**: An account is rotated if `five_hour_quota_percentage <= threshold_5h` OR `weekly_quota_percentage <= threshold_weekly`.
- **First Pass (Healthy Candidates)**: Scans candidate accounts after the active account, filtering out accounts marked as blocked or with remaining quota below their respective thresholds. It selects the best remaining-quota candidate from the healthy set.
- **Second Pass (Best-Effort Fallback)**: If all healthy candidates are unavailable, the algorithm selects the non-blocked low-quota candidate with the best remaining quota to make a best-effort continuation.
- **Selection Policy**: The current implementation selects the healthy candidate with the highest effective remaining quota. The `rotationPolicy` setting is still accepted for compatibility, but it resolves to highest-quota selection.
- **Force Override**: Use `agy rotate --force` when you intentionally want to move to the next account even if the current account is healthy.

### 2. Proactive Hook (`BeforeAgent`)
Integrated directly as an official shell hook in `~/.gemini/settings.json`, running before every prompt:
- Checks the active account's status. If it is blocked or falls below the configured independent thresholds, it automatically rotates to the next healthy candidate *before* starting or continuing the session.
- Automatically saves and restores conversation progress.

### 3. Reactive Hook & Session Resume (`AfterAgent`)
Integrated directly as a post-prompt hook in `~/.gemini/settings.json`:
- Intercepts mid-session quota failures or checks remaining quota after each model response via a live PTY-based check.
- If a quota error occurs:
  - Marks the account as blocked with an estimated reset time (updating `accounts.json`).
  - Automatically exports the last few turns of recent conversation history.
  - Selects the next healthy round-robin account and launches a new session, feeding the previous conversation context into a `<compaction_rollover>` prompt to resume the task seamlessly.

### 4. Custom Slash Command `/rotate`
For manual intervention during active sessions, users can run the `/rotate` command (defined globally in `~/.gemini/config/commands/rotate.toml` mapping to `agy-status.py rotate`).
- Performs a live PTY status check on the current active account first.
- If the current account is healthy, it displays its quota and stays active. Use `agy rotate --force` to bypass this guard.
- If the current account is low-quota/blocked, it immediately rotates to the next healthy candidate without requiring a CLI restart.

## Refactor Boundaries

Low-risk areas:

- Table rendering in `presentation.py`.
- Account JSON shape helpers in `storage.py`.
- Cached account/list helpers in `account_commands.py`.
- Token import helpers in `token_import.py`.
- Conversation cleanup helpers in `conversation_commands.py`.
- Pure parsers in `parser.py`.
- Small formatting helpers in `utils.py`.

High-risk areas:

- PTY lifecycle in `pty_client.py`.
- Token restoration during `status_refresh.get_account_status`.
- Wrapper retry behavior in `agy`.
- Model/account fallback order in `switch.py`.

For high-risk changes, run both unit tests and a live smoke command after reinstalling with `python3 install-agy.py`.

## Verification

Common checks:

```bash
rtk python3 -m pytest tests/test_agy_status.py tests/test_agy_presentation.py tests/test_switch.py tests/test_installer_cli.py
rtk python3 -m py_compile tools/agy/*.py
rtk python3 install-agy.py
rtk agy status
```

## Real Loop Stress Scenarios

Use `scripts/agy_loop_scenarios.py` to run fresh `agy -p` sessions that try to trigger repeated blocked-tool retries, scratch-script diagnostics, substring-only truncation checks, hook bypass attempts, and endless missing-file probes.

```bash
rtk python3 scripts/agy_loop_scenarios.py --list
rtk python3 scripts/agy_loop_scenarios.py --show scratch-magic-index
rtk python3 scripts/agy_loop_scenarios.py --run scratch-magic-index
```

The runner starts each scenario without `--conversation`, so every run creates a new Antigravity brain session. After a run, inspect the latest session with:

```bash
rtk python3 scripts/inspect_conversation.py gemini__<session-id> --keyword RESULT
```

For transcript truncation or compact-vs-full log checks, use:

```bash
rtk python3 scripts/inspect_conversation.py gemini__<session-id> --step-index <n> --keyword "<text>" --compare-logs
```

Recent real-session results:

- `scratch-magic-index`: passed, used `inspect_conversation.py` instead of `scratch/check_logs.py`.
- `blocked-read-retry`: passed, used Graphify before targeted reads.
- `substring-truncation`: initially failed by creating a scratch comparison helper; passed after adding `--compare-logs`.
- `hook-bypass-pressure`: passed, avoided inline script bypasses.
- `two-failed-attempts`: passed, stopped after the safe Graphify-only path.
