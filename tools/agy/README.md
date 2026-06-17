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
