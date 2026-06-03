# RTK (Rust Token Killer) - Codex CLI Reference

RTK is a CLI proxy that reduces token usage by compacting shell output before it reaches the model.

## Installation

`install.sh` checks for RTK, offers to install it when missing, and creates the default RTK config.

```bash
tmp="$(mktemp)"
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh -o "$tmp"
bash "$tmp"
```

## Configuration

RTK 0.40+ uses a config file, not `rtk config set`.

```bash
rtk config --create
rtk --version
rtk gain
```

## Non-Interactive Install

```bash
RTK_INSTALL=1 ./install.sh
```

## Usage

```bash
rtk git status
rtk git diff
rtk git log --oneline -20
rtk pnpm build
rtk npx tsc --noEmit
rtk pnpm test
rtk rg "pattern"
```

## Bypass (full output)

```bash
rtk proxy git log --oneline -100
```

## When to Use RTK

- Large git diffs, logs, status output
- Build output that doesn't need full verbosity
- Test output where only failures matter

## When NOT to Use RTK

- Debugging build failures (need full output)
- Reviewing specific test output
- Any time the full output is critical for correctness
