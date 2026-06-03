---
name: strategic-compact
description: Context window management — smart compaction when context is running low. Use when approaching context limits during long sessions to preserve critical information.
---

# Strategic Compact

Manages context window intelligently during long sessions.

## When to Trigger

- Context usage exceeds 70%
- Before starting a large refactor
- After completing a major feature
- When switching between unrelated tasks

## Compaction Strategy

### Priority 1: Keep (Never Drop)
- Current task requirements
- Active bugs or issues being debugged
- Files currently being edited
- Security findings or blockers
- Test results from current feature

### Priority 2: Summarize
- Completed subtasks (keep conclusions only)
- Code review findings (keep action items)
- Research results (keep key decisions)
- Previous file contents (keep file paths + change summary)

### Priority 3: Drop
- Verbose tool output (build logs, test output)
- Intermediate exploration steps
- Redundant context from multiple reads of same file
- Successful operations with no side effects

## Compaction Process

1. **Audit current context**
   - Identify what's actively needed
   - Flag completed work for summarization
   - Mark redundant context for removal

2. **Create summary checkpoint**
   ```
   ## Context Checkpoint (YYYY-MM-DD HH:MM)

   ### Current Task
   [What we're working on right now]

   ### Completed
   - [Feature A] — done, files: x, y, z
   - [Bug Fix B] — done, root cause: ...

   ### In Progress
   - [Feature C] — 60% done, next: implement hook

   ### Key Decisions
   - Chose X over Y because Z
   - API design uses REST, not GraphQL

   ### Blockers
   - None / [describe]

   ### Files Modified
   - src/feature-a.ts — new feature
   - src/utils.ts — added helper
   ```

3. **Drop low-priority context**
   - Remove verbose outputs
   - Summarize completed work
   - Keep only active file states

4. **Resume from checkpoint**
   - Continue work from summary
   - Re-read files only if needed
   - Maintain task continuity

## Anti-Patterns

- ❌ Compacting mid-debug (loses investigation trail)
- ❌ Dropping security findings
- ❌ Summarizing active code changes (loses line-level context)
- ❌ Compacting when context is < 50% used (unnecessary)

## Integration with Hooks

If PostToolUse hooks are available:
- Auto-suggest compaction at 75% context usage
- Save checkpoint to memory before compact
- Restore critical context after compact

Without hooks (Codex):
- Manually trigger when session feels slow
- Use `/compact` or ask to "save context checkpoint"
- Review checkpoint summary before continuing
