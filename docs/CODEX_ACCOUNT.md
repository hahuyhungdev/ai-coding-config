# Codex Account Helper

`codex-account` manages a local list of Codex ChatGPT auth tokens and swaps the active `~/.codex/auth.json` manually.

The source lives in:

```text
tools/codex-account/codex-account.py
```

## Quick Start

```bash
codex account list
codex account current
codex account use 1
codex account use user@example.com
```

`list` reads cached local metadata only. The `QUOTA` column is derived from the latest local Codex session `token_count.rate_limits` events, similar to the cached `agy account list` pattern. It does not call a live quota API.

The `codex` wrapper intercepts only explicit account-management commands and passes normal Codex usage through to the original binary:

```bash
codex exec "summarize this repo"
codex doctor
codex --version
```

## Account Commands

```bash
codex account add personal
codex account add work --from /path/to/auth.json
codex account add work --from -
codex account relabel
```

- `add` stores the active `~/.codex/auth.json` by default.
- `--from -` reads an auth JSON object from stdin.
- Labels default to the email claim in the token when available.
- `use` accepts a 1-based index, email fragment, or label fragment. Account id matching is supported internally, but ids are not printed by default.
- Mutations create timestamped backups beside the file being changed.

The helper never prints access tokens, refresh tokens, or account ids in normal table output.

The standalone helper remains available as `codex-account` for scripts that want to bypass the `codex` wrapper.
