---
name: switch
description: "Check current account quota and switch to a better account if quota is low. Triggers session rollover to apply the new account."
---

# Account Switch (agy CLI)

You are executing the `/switch` command in the Antigravity CLI (`agy`). This command checks the current account's quota and switches to a healthier account if needed.

## Procedure

1. **Check Current Account Quota**:
   - Run: `agy status --json`
   - Parse the JSON output to get:
     - `active_account`: current account name
     - `five_hour_quota_percentage`: 5-hour session quota (%)
     - `weekly_quota_percentage`: weekly quota (%)
   - Display the current status to the user.

2. **Evaluate Whether to Switch**:
   - **Switch if**: either quota is ≤ 30%
   - **Stay if**: both quotas are > 30%
   - If staying, inform the user: "✅ Account is healthy, no switch needed." and stop.

3. **Switch Account**:
   - Run: `agy rotate`
   - This will automatically select the account with the highest available quota.
   - Display the switch result to the user.

4. **Trigger Session Rollover** (to apply new account):
   - Since the current session is authenticated with the old account's token, a session restart is needed.
   - Save current session progress to `.agy_progress.md` (same format as `/compact`):
     ```markdown
     # Session Progress Summary

     **Date:** YYYY-MM-DD HH:MM
     **Goal:** <Brief description of the main task>
     **Account Switch:** Switched from <old_account> to <new_account> due to low quota.

     ## Completed
     - [x] Task 1
     - [x] Task 2

     ## Pending / Next Steps
     - [ ] Task 3
     ```
   - Then trigger auto-compaction:
     ```bash
     touch ~/.gemini/antigravity-cli/.compact_signal
     PID=$$
     while [ -n "$PID" ] && [ "$PID" -gt 1 ]; do
         if ps -p "$PID" -o comm= | grep -q "agy-bin"; then
             kill "$PID"
             break
         fi
         PID=$(ps -p "$PID" -o ppid= | tr -d ' ')
     done
     ```
   - Inform the user that the session will auto-restart with the new account.

## Important Notes

- **Always show status first** before deciding to switch. The user should see the quota numbers.
- **If `agy status --json` fails**, fall back to `agy status` (text mode) and parse visually.
- **The session rollover is necessary** because the agy-bin process caches the OAuth token in memory. Switching the token file alone won't affect the current session.
- **Don't switch if quota is healthy** — unnecessary switches waste the user's time on a session restart.

## Example Output

```
📊 Current account: hahuyhungdev
   5H Quota: 15% ⚠️  |  Weekly Quota: 45%

⚠️ 5-hour quota is low (≤30%). Switching account...

🔄 Switched to: 01073463578a (Quota: 5H:100%/W:100%)

💾 Saving session progress and restarting to apply new account...
```
