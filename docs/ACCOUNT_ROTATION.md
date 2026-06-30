# Account Rotation Notes

This repo manages account rotation for two local CLI wrappers:

- `agy`: Antigravity CLI wrapper under `tools/agy/`
- `codex`: Codex CLI wrapper under `tools/codex/` with account helper in `tools/codex-account/`

## Shared Policy

Default rotation is threshold-gated. A healthy active account should stay active.

Use `--force` only when you intentionally want to move to the next saved account even though the active account is still healthy:

```bash
agy rotate --force
codex rotate --force
```

## AGY Thresholds

AGY stores quota as remaining percentage.

The active AGY account is low when either condition is true:

- `5H <= threshold_5h`
- `W <= threshold_weekly`

The defaults in code are `threshold_5h=15` and `threshold_weekly=10`, but local runtime settings may override them in `~/.gemini/antigravity-cli/settings.json`.

Example: if local config has `threshold_5h=60`, then an AGY account with `5H:55%/W:92%` is considered low and eligible for default rotation.

## Codex Threshold

Codex session logs expose `used_percent`, not remaining percentage.

The active Codex account is low when the highest known usage window is greater than or equal to `--threshold-used`.

The default is:

```bash
codex rotate --threshold-used 70
```

That is equivalent to rotating when a 5-hour or weekly window has 30% or less remaining.

## Compact Behavior

AGY compaction is a CLI rollover mechanism driven by `.compact_signal` and `.agy_progress.md`.

Do not treat `agy compact` as the source of truth for context compaction semantics. The wrapper handles compacted session resume after the active `agy-bin` process exits.
