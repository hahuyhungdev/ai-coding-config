# Hook Configuration Guide

**Last Updated:** 2026-06-09
**Covers:** How to configure and customize Graphify hooks

---

## 📋 Table of Contents

1. [Basic Configuration](#basic-configuration)
2. [Hook Types](#hook-types)
3. [Configuration Examples](#configuration-examples)
4. [Advanced Configuration](#advanced-configuration)
5. [Troubleshooting](#troubleshooting)

---

## Basic Configuration

### Where are hooks configured?

Hooks are configured in two locations:

1. **Project-level:** `.claude/settings.json`
2. **Global-level:** `~/.claude/settings.json`

**Priority:** Project-level overrides global-level

---

### Basic settings.json structure:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "your-hook-command-here"
          }
        ]
      }
    ]
  }
}
```

---

## Hook Types

### 1. PreToolUse Hooks

**When:** Before tool execution
**Purpose:** Block or modify tool calls

**Matchers:**
- `Bash` - Shell commands
- `Read` - File reading
- `Grep` - Code search
- `Edit` - File editing
- `Write` - File writing

**Example:**
```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "your-validation-script"
    }
  ]
}
```

---

### 2. PostToolUse Hooks

**When:** After tool execution
**Purpose:** Post-processing, logging, notifications

**Example:**
```json
{
  "matcher": "Write|Edit",
  "hooks": [
    {
      "type": "command",
      "command": "pnpm prettier --write \"$FILE_PATH\""
    }
  ]
}
```

---

## Configuration Examples

### Example 1: Graphify Hook (Current)

**Purpose:** Block codebase exploration, encourage graphify usage

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 '/path/to/graphify-hook-improved.py'"
          }
        ]
      },
      {
        "matcher": "Read|Glob",
        "hooks": [
          {
            "type": "command",
            "command": "python3 '/path/to/graphify-hook-improved.py'"
          }
        ]
      }
    ]
  }
}
```

---

### Example 2: Format on Save

**Purpose:** Auto-format code after edits

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "pnpm prettier --write \"$FILE_PATH\"",
            "description": "Format edited files"
          }
        ]
      }
    ]
  }
}
```

---

### Example 3: Lint Check

**Purpose:** Run linter after edits

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "pnpm eslint --fix \"$FILE_PATH\"",
            "description": "Lint edited files"
          }
        ]
      }
    ]
  }
}
```

---

### Example 4: Type Check

**Purpose:** Run type checker after edits

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "timeout 60 pnpm tsc --noEmit --pretty false --incremental",
            "description": "Type-check after edits"
          }
        ]
      }
    ]
  }
}
```

---

### Example 5: File Size Guard

**Purpose:** Block oversized file writes

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "node -e \"let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{const i=JSON.parse(d);const c=i.tool_input?.content||'';const lines=c.split('\\n').length;if(lines>800){console.error('[Hook] BLOCKED: File exceeds 800 lines');process.exit(2)}console.log(d)})\"",
            "description": "Block writes exceeding 800 lines"
          }
        ]
      }
    ]
  }
}
```

---

### Example 6: Security Guard

**Purpose:** Block sensitive file access

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read",
        "hooks": [
          {
            "type": "command",
            "command": "node -e \"const d=JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));const f=d.tool_input?.file_path||'';if(f.match(/\\.(env|pem|key)$/)){console.error('BLOCKED: Sensitive file');process.exit(2)}console.log(JSON.stringify(d))\"",
            "description": "Block access to sensitive files"
          }
        ]
      }
    ]
  }
}
```

---

## Advanced Configuration

### Multiple Hooks

You can chain multiple hooks:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "pnpm prettier --write \"$FILE_PATH\"",
            "description": "Format"
          },
          {
            "type": "command",
            "command": "pnpm eslint --fix \"$FILE_PATH\"",
            "description": "Lint"
          },
          {
            "type": "command",
            "command": "timeout 60 pnpm tsc --noEmit",
            "description": "Type check"
          }
        ]
      }
    ]
  }
}
```

**Order:** Hooks run in sequence (format → lint → type check)

---

### Conditional Hooks

Use shell logic for conditional execution:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "case \"$FILE_PATH\" in *.ts|*.tsx) pnpm prettier --write \"$FILE_PATH\" ;; *.py) black \"$FILE_PATH\" ;; esac",
            "description": "Format based on file type"
          }
        ]
      }
    ]
  }
}
```

---

### Environment Variables

Access environment variables in hooks:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "if [ \"$GRAPHIFY_DEBUG\" = \"1\" ]; then echo \"File edited: $FILE_PATH\" >&2; fi",
            "description": "Debug logging"
          }
        ]
      }
    ]
  }
}
```

---

### Custom Scripts

Use external scripts for complex logic:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 '/path/to/custom-hook.py'",
            "description": "Custom validation"
          }
        ]
      }
    ]
  }
}
```

**custom-hook.py:**
```python
import json
import sys

data = json.load(sys.stdin)
command = data.get('tool_input', {}).get('command', '')

# Your custom logic here
if 'dangerous' in command:
    print('BLOCKED: Dangerous command', file=sys.stderr)
    sys.exit(2)

print(json.dumps(data))
```

---

## Ordering

Recommended hook order:

1. **Format** (prettier, black)
2. **Lint** (eslint, pylint)
3. **Type check** (tsc, mypy)
4. **Build verification** (optional)

**Example:**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {"type": "command", "command": "prettier --write \"$FILE_PATH\""},
          {"type": "command", "command": "eslint --fix \"$FILE_PATH\""},
          {"type": "command", "command": "tsc --noEmit"}
        ]
      }
    ]
  }
}
```

---

## Troubleshooting

### Hook not running

**Check:**
1. Settings syntax valid?
2. Matcher correct?
3. Command executable?

**Debug:**
```bash
# Test hook manually
echo '{"tool_input":{"command":"test"}}' | python3 your-hook.py

# Check settings
cat .claude/settings.json | python3 -m json.tool
```

---

### Hook running at wrong time

**Check:**
1. Matcher pattern correct?
2. PreToolUse vs PostToolUse?
3. Tool name correct?

**Common matchers:**
- `Bash` - Shell commands
- `Read` - File reading
- `Write` - File writing
- `Edit` - File editing
- `Grep` - Code search

---

### Hook blocking legitimate operations

**Solutions:**
1. Add context detection
2. Use bypass mechanism
3. Improve error messages

**Example:**
```bash
# Debug mode
GRAPHIFY_DEBUG=1 claude -p "test"

# Bypass mode
GRAPHIFY_BYPASS=1 claude -p "test"
```

---

### Hook performance issues

**Optimizations:**
1. Cache hook results
2. Use fast scripts
3. Avoid heavy I/O
4. Use incremental checks

**Example:**
```json
{
  "command": "timeout 60 pnpm tsc --noEmit --incremental"
}
```

---

## 📚 Related Documentation

- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues
- [Hook Improvements](../HOOK_IMPROVEMENTS.md) - Recent changes
- [Graphify FAQ](GRAPHIFY_FAQ.md) - Graphify usage
- [README](../README.md#hooks) - Hook documentation

---

**Last Updated:** 2026-06-09
**Maintainer:** AI Assistant