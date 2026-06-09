# Troubleshooting Guide

**Last Updated:** 2026-06-09
**Covers:** Common issues and solutions for AI-Coding-Config

---

## 🔍 Quick Diagnosis

### Symptom: "BLOCKED by graphify hook"

**Cause:** Hook is blocking codebase exploration

**Solutions:**

1. **Use graphify instead:**
   ```bash
   rtk graphify query "your question"
   ```

2. **Check quota (if blocked after 3 calls):**
   ```bash
   # Wait for new session or use bypass
   GRAPHIFY_BYPASS=1 claude -p "your question"
   ```

3. **Debug hook decisions:**
   ```bash
   GRAPHIFY_DEBUG=1 claude -p "your question"
   ```

---

### Symptom: "Maximum 3 Graphify discovery calls reached"

**Cause:** Session quota exceeded

**Solutions:**

1. **Start new session:**
   ```bash
   claude  # New session resets quota
   ```

2. **Use bypass (temporary):**
   ```bash
   GRAPHIFY_BYPASS=1 claude -p "your question"
   ```

3. **Synthesize from available context:**
   - Review previous graphify results
   - Use GRAPH_REPORT.md for overview
   - Read specific files with Read tool

---

### Symptom: Hook not working / old behavior

**Cause:** Settings not loaded or cached

**Solutions:**

1. **Restart Claude Code:**
   - Close and reopen terminal
   - Or start new claude session

2. **Verify settings:**
   ```bash
   # Check project settings
   cat .claude/settings.json

   # Check global settings
   cat ~/.claude/settings.json
   ```

3. **Reinstall hooks:**
   ```bash
   python3 install.py --claude --force
   ```

---

### Symptom: graphify command not found

**Cause:** graphify not installed or not in PATH

**Solutions:**

1. **Check installation:**
   ```bash
   which graphify
   graphify --version
   ```

2. **Install graphify:**
   ```bash
   pip install graphify
   # or
   npm install -g graphify
   ```

3. **Use rtk wrapper:**
   ```bash
   rtk graphify query "your question"
   ```

---

### Symptom: graphify-out/graph.json missing

**Cause:** Graph not generated

**Solutions:**

1. **Generate graph:**
   ```bash
   graphify update .
   ```

2. **Reinstall graphify:**
   ```bash
   python3 install.py --claude --force
   ```

3. **Check project root:**
   ```bash
   ls -la graphify-out/
   ```

---

## 🛠️ Hook Issues

### Issue: Hook blocking legitimate operations

**Diagnosis:**
```bash
GRAPHIFY_DEBUG=1 claude -p "your command" 2>&1 | grep GRAPHIFY_HOOK_DEBUG
```

**Common causes:**

1. **Context detection failing:**
   - Check if command contains debug/build keywords
   - Use GRAPHIFY_BYPASS=1 as workaround

2. **File extension in blocked list:**
   - .py, .ts, .js, .md, etc. are blocked for exploration
   - Use Edit tool directly for modifications

3. **Search tool in command:**
   - find, grep, rg, etc. are blocked
   - Use graphify query instead

---

### Issue: Hook not blocking exploration

**Diagnosis:**
```bash
# Check if graphify-out exists
ls -la graphify-out/graph.json

# Check settings
cat .claude/settings.json | grep -A5 hooks
```

**Common causes:**

1. **graphify-out/graph.json missing:**
   - Hook only blocks when graph exists
   - Generate graph first

2. **Settings not loaded:**
   - Restart Claude Code
   - Check settings syntax

---

### Issue: Debug logging not working

**Diagnosis:**
```bash
GRAPHIFY_DEBUG=1 echo "test" 2>&1 | grep GRAPHIFY_HOOK_DEBUG
```

**Solutions:**

1. **Check environment variable:**
   ```bash
   export GRAPHIFY_DEBUG=1
   ```

2. **Check stderr:**
   ```bash
   GRAPHIFY_DEBUG=1 claude -p "test" 2>/tmp/debug.log
   cat /tmp/debug.log
   ```

---

## 📊 Graphify Issues

### Issue: Query returns no results

**Possible causes:**

1. **Graph not generated:**
   ```bash
   graphify update .
   ```

2. **Query too specific:**
   ```bash
   # Try broader query
   rtk graphify query "project structure"
   ```

3. **Graph corrupted:**
   ```bash
   rm -rf graphify-out/
   graphify update .
   ```

---

### Issue: Query returns too many results

**Solutions:**

1. **Narrow query:**
   ```bash
   rtk graphify query "TradingBot class methods"
   ```

2. **Use context_filter:**
   ```bash
   rtk graphify query "authentication" --context-filter="call"
   ```

3. **Limit depth:**
   ```bash
   rtk graphify query "main components" --depth=1
   ```

---

### Issue: Graphify slow on large codebase

**Solutions:**

1. **Use scoped queries:**
   ```bash
   rtk graphify query "auth module" --scope="libs/auth"
   ```

2. **Check graph size:**
   ```bash
   ls -lh graphify-out/graph.json
   ```

3. **Regenerate with filters:**
   ```bash
   graphify update . --exclude="node_modules,dist"
   ```

---

## 🔧 Installation Issues

### Issue: install.py fails

**Common errors:**

1. **Permission denied:**
   ```bash
   chmod +x install.py
   python3 install.py --claude
   ```

2. **Missing dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Invalid project directory:**
   ```bash
   python3 install.py --claude --project /path/to/project
   ```

---

### Issue: Settings not applied after install

**Solutions:**

1. **Restart Claude Code:**
   - Close terminal
   - Open new terminal
   - Start claude

2. **Verify installation:**
   ```bash
   cat .claude/settings.json
   cat ~/.claude/settings.json
   ```

3. **Force reinstall:**
   ```bash
   python3 install.py --claude --force
   ```

---

## 🐛 Common Bugs

### Bug: Hook blocks claude CLI commands

**Status:** Fixed in v2.0

**Workaround:**
```bash
GRAPHIFY_BYPASS=1 claude -p "your command"
```

**Fix:**
```bash
python3 install.py --claude --force
```

---

### Bug: Error messages not helpful

**Status:** Fixed in v2.0

**Workaround:**
```bash
GRAPHIFY_DEBUG=1 claude -p "your command"
```

**Fix:**
```bash
python3 install.py --claude --force
```

---

### Bug: Quota not resetting between sessions

**Diagnosis:**
```bash
ls -la /tmp/ai-coding-config-graphify-*.count
```

**Solution:**
```bash
rm -f /tmp/ai-coding-config-graphify-*.count
```

---

## 📞 Getting Help

### Check logs:
```bash
# Debug mode
GRAPHIFY_DEBUG=1 claude -p "test" 2>/tmp/debug.log
cat /tmp/debug.log

# Verbose mode
claude --debug -p "test"
```

### Check configuration:
```bash
# Project settings
cat .claude/settings.json

# Global settings
cat ~/.claude/settings.json

# Graphify output
ls -la graphify-out/
```

### Reset everything:
```bash
# Remove graphify
rm -rf graphify-out/

# Reinstall
python3 install.py --claude --force

# Restart Claude Code
```

### Report issue:
1. Check this guide first
2. Run with GRAPHIFY_DEBUG=1
3. Include debug output
4. Describe expected vs actual behavior

---

## 📚 Related Documentation

- [Hook Improvements](../HOOK_IMPROVEMENTS.md) - Hook system changes
- [Hook Summary](../HOOK_IMPROVEMENTS_SUMMARY.md) - Implementation details
- [Improvement Plan](../IMPROVEMENT_PLAN.md) - Overall improvement roadmap
- [Graphify Usage](../README.md#graphify) - Graphify documentation

---

**Last Updated:** 2026-06-09
**Maintainer:** AI Assistant