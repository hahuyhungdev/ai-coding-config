# RTK (Rust Token Killer) — Codex CLI Reference

RTK is a CLI proxy that reduces token usage by compacting shell output before it reaches the model.

## Installation

```bash
curl -sSL https://rtk.apidocumentation.com/install.sh | bash
```

## Configuration

```bash
rtk config set default.provider openai
rtk config set default.model gpt-5.5
rtk config set default.maxTokens 16000
rtk config set default.cachePrompt true
```

## Environment Variables

```bash
export OPENAI_API_KEY="sk-..."
export RTK_DEFAULT_PROVIDER=openai
export RTK_DEFAULT_MODEL=gpt-5.5
```

## Usage

```bash
rtk git status
rtk git diff
rtk git log --oneline -20
rtk pnpm build
rtk npx tsc --noEmit
rtk pnpm test
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
