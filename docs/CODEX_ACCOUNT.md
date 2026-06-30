# Codex Account Helper

`codex-account` manages a local list of Codex ChatGPT auth tokens and swaps the active `~/.codex/auth.json` manually.

The source lives in:

```text
tools/codex-account/codex-account.py
```

For shared AGY/Codex rotation semantics, see [ACCOUNT_ROTATION.md](ACCOUNT_ROTATION.md).

## Quick Start

```bash
codex ls
codex status
codex check
codex status --json
codex check hahuyhungdev --json
codex rotate --dry-run
codex rotate
codex current
codex token
codex login-temp
codex add active-copy
codex switch hahuyhungdev
```

## Short Command Guide

Use these most of the time:

```bash
codex ls                    # cached account table
codex status                # live quota check for all accounts
codex check [account]       # live quota check; account is optional alias
codex rotate --dry-run      # preview automatic switch
codex rotate                # switch when current account is low
codex token [label]         # paste a refresh token safely
codex login-temp [label]    # browser/URL login in a temporary CODEX_HOME
codex add <label>           # save the current active auth.json
codex switch <account>      # manually swap active auth.json
codex current               # show the active account
```

You normally do not need to run `codex-account` directly. It is the internal helper behind `codex account ...` and the short `codex ...` commands.

`list` reads cached local metadata only. The `LEFT` column is derived from the latest local Codex session `token_count.rate_limits` events, similar to the cached `agy account list` pattern. It does not call a live quota API.

Use `codex status` when the quota must be checked live. It runs a tiny `codex-bin exec --json` for each saved account inside a temporary `CODEX_HOME`, reads the new sandbox session log, and stores the resulting `rate_limits_snapshot` back into `accounts.json`. This is the Codex equivalent of the `agy status` refresh path. The real active `auth.json` is not swapped during the check. `codex check` is kept as a live-refresh alias, and `codex status --no-refresh` is available when you explicitly want cached data.

If a live check returns a Codex usage-limit error instead of a rate-limit snapshot, `status` marks that account as `exhausted` with `0%` left. Other refresh failures are marked `stale` so cached percentages are not mistaken for current quota.

When you just added or updated one auth file, prefer a targeted refresh:

```bash
codex check hahuyhungdev --json
```

`codex check <account>` accepts a 1-based index, label, email fragment, or account id fragment. It uses a 30-second per-account timeout by default, so it keeps a broken login from making the whole refresh look stuck. Progress is printed to stderr even when JSON mode is enabled. Set `CODEX_ACCOUNT_CHECK_TIMEOUT=60` when you want a longer default timeout.

Codex rate-limit events expose `used_percent`. The helper converts that to remaining quota for the JSON `quota` field and text `LEFT` display, and also exposes `usage` plus `used_percent` for diagnostics. `status` live-refreshes by default, while `list` and `status --no-refresh` use cached snapshots. `status` and default `rotate` treat an account as low when either usage window is at or above `70%` by default, which is equivalent to the `agy` convention of switching at `30%` remaining. A usage-limit refresh error is treated as exhausted rather than healthy cached quota. A healthy active account stays active unless `codex rotate --force` is used. Accounts without cached usage are not selected automatically unless `--allow-unknown` is passed.

The `codex` wrapper intercepts only explicit account-management commands and passes normal Codex usage through to the original binary:

```bash
codex exec "summarize this repo"
codex doctor
codex --version
```

## Account Commands

```bash
codex account list
codex account add personal
codex account add work --from /path/to/auth.json
codex account add work --from -
codex account add-token work
codex account add-token work --from /path/to/refresh-token.txt
codex account relabel
codex account status --json
codex account status --refresh --json
codex account status --no-refresh --json
codex account status --refresh --account work --timeout 30 --json
codex account rotate --dry-run --json
codex account rotate --force
codex account rotate --allow-unknown
```

- `add` stores the active `~/.codex/auth.json` by default.
- Short aliases `codex ls`, `codex check`, `codex rotate`, `codex current`, `codex token`, `codex add`, `codex switch`, and `codex use` route to the same helper as `codex account ...`.
- `--from -` reads an auth JSON object from stdin.
- `add-token` / `token` reads a Codex ChatGPT refresh token from stdin/prompt by default and wraps it into a minimal auth JSON. Do not pass tokens as command-line arguments.
- Labels default to the email claim when available. Token-only adds use a `pasted-token-YYYYmmdd-HHMMSS` label when you omit one.
- `use` accepts a 1-based index, email fragment, or label fragment. Account id matching is supported internally, but ids are not printed by default.
- `status` reports cached usage health for each saved account and never mutates `auth.json`.
- `status --refresh` performs the sandbox live check first, updates saved account snapshots, then reports the refreshed status.
- `status --refresh --account <target>` checks only one saved account. This is the fastest way to validate a newly added auth JSON.
- `rotate` backs up `auth.json`, then swaps to the healthiest saved account with known cached usage. Use `--dry-run` first to inspect the chosen target.
- Mutations create timestamped backups beside the file being changed.

The helper never prints access tokens, refresh tokens, or account ids in normal table output.

The standalone helper remains available as `codex-account` for scripts that want to bypass the `codex` wrapper.

## Paste Token Or Sandbox Login

For a direct refresh-token paste:

```bash
codex token
# paste the refresh token, then press Enter / Ctrl-D
codex ls
codex check <shown-label> --json
```

If you want to log in through Codex without touching the main active account, use a temporary `CODEX_HOME`:

```bash
codex login-temp
```

That uses Codex's default browser/URL login flow, writes only to the temporary directory, saves the logged-in auth into the account list, and runs a targeted check. The active `~/.codex/auth.json` is unchanged until you explicitly run `codex rotate` or `codex switch`.

If you specifically want the device-code flow, use:

```bash
codex login-temp --device-auth
```
