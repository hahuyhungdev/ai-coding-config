---
name: compact
description: "Summarize the active session's progress and automatically restart the agy CLI to compact context."
---

# Strategic Context Compaction (agy CLI)

You are executing the `/compact` command in the Antigravity CLI (`agy`). Since `agy` does not have a native in-memory context compaction tool, you must automatically perform a session rollover to save token usage and speed up responses.

## Compaction Procedure

1. **Analyze Current State**:
   - Identify all files modified in the active session.
   - List completed tasks.
   - List pending tasks.

2. **Save to Progress File**:
   - Write a structured, concise summary into a file named `.agy_progress.md` in the root of the workspace. (This file is ignored by git).
   - Use relative file links to ensure environment privacy and bypass the path leak checker.
   - Example format for `.agy_progress.md`:
     ```markdown
     # Session Progress Summary

     **Date:** YYYY-MM-DD HH:MM
     **Goal:** <Brief description of the main task>

     ## Completed
     - [x] Task 1
     - [x] Task 2

     ## Pending / Next Steps
     - [ ] Task 3
     - [ ] Task 4

     ## Active Files Modified
     - [file.py](file:///path/to/file.py)
     ```

3. **Trigger Auto-Compaction, Rotate & Exit**:
   - Run the following command to save progress, rotate the active account, set the reload signal, and cleanly restart the TUI session:
     ```bash
     python3 tools/agy/switch_session.py
     ```
   - Respond to the user: Inform them that you have successfully saved the session state to `.agy_progress.md`, rotated the active account, and are initiating a seamless automatic session rollover. The shell wrapper will automatically read the progress file and resume the session with your summary. Do NOT ask the user to exit manually.

---

## When to Use
Suggest running the `/compact` command to the user at logical task boundaries or when the following conditions are met:
- **High Token Pressure**: The session is running long and responses start slowing down or losing coherence.
- **Phase Transitions**: Switching from research/planning to active implementation, or after completing a major milestone.
- **Context Shifts**: Clearing out messy debugging traces before starting a new feature or task.

### Compaction Decision Guide

| Phase Transition | Compact? | Why |
| :--- | :--- | :--- |
| Research → Planning | **Yes** | Research context is bulky; plan is the distilled output. |
| Planning → Implementation | **Yes** | Once the plan is saved in a file, free up context for coding. |
| Implementation → Testing | **Maybe** | Keep if tests reference recent code; compact if switching focus. |
| Debugging → Next feature | **Yes** | Debug traces pollute context for unrelated work. |
| Mid-implementation | **No** | Do not compact; losing variable names, file paths, and partial state is costly. |
| After a failed approach | **Yes** | Clear the dead-end reasoning before trying a new approach. |

### What Survives Compaction

| Persists | Lost |
| :--- | :--- |
| `CLAUDE.md` / `AGY.md` guidelines | Intermediate reasoning and analysis |
| Git state (commits, branches) | Tool call history and counts |
| Files on disk | Unsaved verbal preferences stated in chat |

### Best Practices
1. **Compact after planning** — Once the plan is finalized in a file or instructions, compact to start implementation fresh.
2. **Compact after debugging** — Clear error-resolution context before continuing.
3. **Don't compact mid-implementation** — Preserve active context for related changes.
4. **Write/Save before compacting** — Ensure all progress, decisions, or code changes are saved to files before initiating a rollover.
