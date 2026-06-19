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

4. **Inform the User**:
   - Tell the user: "✅ Account rotated on disk. The new account will be used on the **next session**."
   - Explain: The current session still uses the old account's cached token in memory. This is normal.
   - Suggest: "Run `/compact` now if you want to restart immediately with the new account."

## Important Notes

- **Always show status first** before deciding to switch. The user should see the quota numbers.
- **If `agy status --json` fails**, fall back to `agy status` (text mode) and parse visually.
- **No session restart** — `agy-bin` caches the OAuth token in memory, so the current session continues with the old account. The new account applies on the next session start (or after `/compact`).
- **Don't switch if quota is healthy** — unnecessary switches waste rotation cycles.

## Example Output

```
📊 Current account: hahuyhungdev
   5H Quota: 15% ⚠️  |  Weekly Quota: 45%

⚠️ 5-hour quota is low (≤30%). Switching account...

🔄 Switched to: 01073463578a (Quota: 5H:100%/W:100%)

✅ Account rotated on disk. The new account will be used on the next session.
💡 Run /compact now if you want to restart immediately with the new account.
```
