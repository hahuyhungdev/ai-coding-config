# RTK (Rust Token Killer) — Claude Code Reference

RTK is a CLI proxy that reduces token usage by compacting shell output (git, npm, pnpm, docker, etc.) before it reaches the model.

## Installation

```bash
curl -sSL https://rtk.apidocumentation.com/install.sh | bash
```

## Configuration

```bash
rtk config set default.provider anthropic
rtk config set default.model claude-opus-4-6
rtk config set default.maxTokens 16000
rtk config set default.cachePrompt true
```

## Environment Variables

```bash
export ANTHROPIC_AUTH_TOKEN="sk-ant-..."
export RTK_DEFAULT_PROVIDER=anthropic
export RTK_DEFAULT_MODEL=claude-opus-4-6
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

## Integration with Claude Code Hooks

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "command": "node ~/.claude/hooks/pre-bash-rtk.js",
        "description": "RTK optimization for shell commands"
      }
    ]
  }
}
```

## When to Use RTK

- Large git diffs, logs, status output
- Build output that doesn't need full verbosity
- Test output where only failures matter

## When NOT to Use RTK

- Debugging build failures (need full output)
- Reviewing specific test output
- Any time the full output is critical for correctness
