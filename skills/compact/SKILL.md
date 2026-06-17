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

3. **Trigger Auto-Compaction & Exit**:
   - Run a bash command to:
     1. Create the signal file: `touch ~/.gemini/antigravity-cli/.compact_signal`
     2. Find the parent `agy-bin` process and terminate it cleanly:
        ```bash
        PID=$$
        while [ -n "$PID" ] && [ "$PID" -gt 1 ]; do
            if ps -p "$PID" -o comm= | grep -q "agy-bin"; then
                kill "$PID"
                break
            fi
            PID=$(ps -p "$PID" -o ppid= | tr -d ' ')
        done
        ```
   - Respond to the user: Inform them that you have successfully saved the session state to `.agy_progress.md` and are initiating a seamless automatic session rollover. The shell wrapper will automatically read the progress file, delete it from disk, and resume the session with your summary. Do NOT ask the user to exit manually.
