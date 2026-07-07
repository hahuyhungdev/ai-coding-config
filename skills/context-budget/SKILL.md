---
name: context-budget
description: Audits context window consumption across agents, skills, rules, and MCP servers, and manages manual session compaction and rollover to save tokens.
---

# Context Budget & Compaction Management

This skill handles token overhead analysis and context window compaction to ensure the active session remains fast, coherent, and within limits.

## When to Use

Use this skill when session context is bloated, latency is high, skills or MCPs need overhead auditing, or a long-running task needs a controlled compaction/rollover checkpoint. Do not use it for ordinary short tasks.

## 1. Context Overhead Audit

Use this flow to audit loaded components when session quality degrades or before adding new skills/MCPs.

### Inventory Targets
- **Skills (`skills/*/SKILL.md`):** Flag files > 400 lines (lazy-load candidates) or overlapping/redundant skills.
- **Agents:** Flag description > 30 words (loads into system prompt) or orphaned files.
- **MCP Servers:** Verify enabled servers via `python3 scripts/mcp-toggle.py list`. Consider disabling unnecessary ones (`python3 scripts/mcp-toggle.py disable <name>`).
- **Rules (`AGENTS.md`):** Flag rules exceeding 300 lines or repeating skill guidelines.

### Token Savings Table Format
```
| Component | Type | Est. Tokens | Recommendation |
|-----------|------|-------------|----------------|
| skill_name| skill| ~1200       | Keep           |
```

---

## 2. Session Compaction & Rollover

When the session is running long and responses slow down, execute a clean session rollover.

### Compaction Procedure
1. **Summarize State:** Identify modified files, completed tasks, and pending next steps.
2. **Save Progress File:** Write a concise summary into a file named `.agy_progress.md` in the root of the workspace. (This file is ignored by git). Use relative file links.
   - *Example `.agy_progress.md` content:*
     ```markdown
     # Session Progress Summary
     **Goal:** <Brief description of the main task>
     ## Completed
     - [x] Task 1
     ## Pending
     - [ ] Task 2
     ## Modified Files
     - [file.py](./file.py)
     ```
3. **Execute Rollover:** Cleanly restart the active TUI session using the session switcher script:
   ```bash
   python3 tools/agy/switch_session.py
   ```
4. **Respond to User:** Inform the user that progress is saved, account rotated, and that the shell wrapper is automatically reloading the session. Do not ask them to exit manually.

### Compaction Decision Guide
- **Compact when:** Transitioning from Planning to Implementation, completing a major milestone, or clearing out heavy error traces.
- **Do NOT compact when:** Mid-implementation (to avoid losing variable context, paths, or active logical state).
