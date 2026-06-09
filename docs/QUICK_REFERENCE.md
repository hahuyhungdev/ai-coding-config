# Quick Reference Card

**Print this or keep it handy!**

---

## 🔍 Graphify Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `query` | General questions | `rtk graphify query "project structure"` |
| `explain` | Deep dive | `rtk graphify explain "auth flow"` |
| `path` | Find relationships | `rtk graphify path "A" "B"` |

---

## 🛠️ Debug & Bypass

| Command | Purpose |
|---------|---------|
| `GRAPHIFY_DEBUG=1` | See hook decisions |
| `GRAPHIFY_BYPASS=1` | Temporarily disable hooks |

**Example:**
```bash
GRAPHIFY_DEBUG=1 claude -p "test"
GRAPHIFY_BYPASS=1 claude -p "test"
```

---

## 📊 Quota System

| Limit | Value |
|-------|-------|
| Discovery calls per session | 3 |
| Initial query | 1 (required) |
| Follow-up queries | 2 (optional) |

**Reset:** Start new Claude session

---

## 🚀 RTK Commands

| Command | Purpose |
|---------|---------|
| `rtk git status` | Compact git status |
| `rtk git diff` | Compact diff |
| `rtk pnpm build` | Compact build output |
| `rtk graphify query` | Graphify with RTK |

---

## 🔧 Maintenance

| Command | Purpose |
|---------|---------|
| `python3 install.py --claude` | Install for Claude |
| `python3 install.py --claude --force` | Force reinstall |
| `graphify update .` | Regenerate graph |

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `.claude/settings.json` | Project hooks |
| `~/.claude/settings.json` | Global hooks |
| `CLAUDE.md` | Project instructions |
| `graphify-out/graph.json` | Knowledge graph |
| `graphify-out/GRAPH_REPORT.md` | Architecture report |

---

## 🎯 Query Examples

### Architecture
```bash
rtk graphify query "project structure and main components"
rtk graphify query "what are the main modules?"
rtk graphify query "how is the codebase organized?"
```

### Dependencies
```bash
rtk graphify query "how do libraries depend on each other?"
rtk graphify query "what does TradingBot import?"
rtk graphify path "front-office" "fe-shared"
```

### Code Understanding
```bash
rtk graphify query "TradingBot class and its methods"
rtk graphify explain "authentication flow"
rtk graphify explain "error handling strategy"
```

### Boundaries
```bash
rtk graphify query "what are the architectural boundaries?"
rtk graphify query "what can import what?"
rtk graphify query "module boundary policy"
```

---

## 🐛 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| "BLOCKED by hook" | Use `graphify query` instead |
| "Quota exceeded" | Start new session or use bypass |
| Hook not working | Restart Claude Code |
| graphify not found | Run `install.py --claude` |
| No results | Run `graphify update .` |

---

## 📞 Help Commands

```bash
# Debug mode
GRAPHIFY_DEBUG=1 claude -p "test"

# Check settings
cat .claude/settings.json

# Check graph
ls -la graphify-out/

# Reinstall
python3 install.py --claude --force
```

---

## 🎓 Workflow

### 1. Explore Architecture
```bash
rtk graphify query "project overview"
rtk graphify query "main components"
rtk graphify query "tech stack"
```

### 2. Understand Code
```bash
rtk graphify query "TradingBot class"
rtk graphify explain "how it works"
rtk graphify path "input" "output"
```

### 3. Debug Issues
```bash
GRAPHIFY_DEBUG=1 claude -p "test"
# Check debug output
# Fix issue
# Test again
```

### 4. Optimize Tokens
```bash
rtk git status  # Not: git status
rtk pnpm build  # Not: pnpm build
```

---

## 📚 Full Documentation

- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Graphify FAQ](GRAPHIFY_FAQ.md)
- [Hook Configuration](HOOK_CONFIGURATION.md)
- [Best Practices](BEST_PRACTICES.md)
- [README](../README.md)

---

**Version:** 2.0
**Last Updated:** 2026-06-09