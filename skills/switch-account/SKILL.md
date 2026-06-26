---
name: switch-account
description: "Check current account health and switch to a better saved account when usage/quota is low. Supports Codex and agy."
---

# Account Switch

You are executing the `/switch-account` command. First detect which CLI is active, then check account health and rotate only when needed.

## Codex Procedure

Use this path when running inside Codex CLI or when the user asks about Codex account switching.

1. **Check Current Account Usage**:
   - Run: `codex check --json`
   - If the user is validating one newly added account, run: `codex check <label-or-index> --json`
   - To add a new account, prefer `codex login-temp [label]` for browser/URL login or `codex token [label]` for pasted refresh tokens.
   - Use `codex login-temp --device-auth [label]` only when you specifically want the device-code flow.
   - Parse the JSON output:
     - `active.label`: current saved account label
     - `active.quota`: refreshed Codex quota-left string
     - `active.usage`: refreshed Codex usage string
     - `active.status`: `healthy`, `low`, or `unknown`
     - `active.used_percent`: highest refreshed usage window
     - `refresh_errors`: accounts that could not be checked live
   - Display the current status to the user.

2. **Evaluate Whether to Switch**:
   - Codex session logs expose `used_percent`, not remaining quota.
   - **Switch if**: active status is `low` or the user explicitly asks to rotate.
   - **Stay if**: active status is `healthy`.
   - **Unknown**: do not rotate automatically unless the user accepts `--allow-unknown`.

3. **Preview and Switch Account**:
   - Run first: `codex rotate --dry-run`
   - If the target is acceptable, run: `codex rotate`
   - Display the switch result to the user.

4. **Inform the User**:
   - Tell the user: "Account rotated on disk. The new account will be used on the next Codex session."
   - Explain: The current session may keep the old auth token in memory. This is normal.
   - Suggest: "Run `/compact` now if you want to restart immediately with the new account."

## agy Procedure

Use this path when running inside Antigravity CLI (`agy`) or when the user asks about `agy`.

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
   - Tell the user: "Account rotated on disk. The new account will be used on the next session."
   - Explain: The current session still uses the old account's cached token in memory. This is normal.
   - Suggest: "Run `/compact` now if you want to restart immediately with the new account."

## Important Notes

- **Always show status first** before deciding to switch. The user should see the quota numbers.
- **Codex `check` is live-ish**: it runs a minimal Codex exec in a temporary `CODEX_HOME` for each saved account, then caches the resulting session `rate_limits` snapshot.
- **Use targeted refresh for one account**: `codex check <target> --json` avoids waiting for every saved account when only one token was just added or fixed.
- **Codex `ls`/`list` is cached** from local saved snapshots/session rate-limit events; use `codex check --json` when deciding whether to switch.
- **Codex output has both left and used**: `quota` is remaining quota, while `usage` and `used_percent` are consumed quota. Rotation decisions use `used_percent`.
- **Codex threshold semantics differ from agy internally**: Codex logs `used_percent`, so `70% used` is equivalent to `30% remaining`.
- **If `agy status --json` fails**, fall back to `agy status` (text mode) and parse visually.
- **No session restart** — the current CLI may cache the OAuth token in memory, so the current session can continue with the old account. The new account applies on the next session start (or after `/compact`).
- **Don't switch if quota is healthy** — unnecessary switches waste rotation cycles.

## Codex Example Output

```
Active: plus-account | low | left 5H:15%/W:80% | used 5H:85%/W:20% | reset 5H:Mon 18:34/W:Fri 18:13

IDX  A  LABEL                          STATUS    LEFT           USED           RESET
1    *  plus-account                   low       5H:15%/W:80%   5H:85%/W:20%   5H:Mon 18:34/W:Fri 18:13

Preview:
Would switch Codex account to 'k12-account' (5H:75%/W:60%)

Account rotated on disk. The new account will be used on the next Codex session.
Run /compact now if you want to restart immediately with the new account.
```

## agy Example Output

```
Current account: hahuyhungdev
5H Quota: 15% | Weekly Quota: 45%

5-hour quota is low (≤30%). Switching account...

Switched to: 01073463578a (Quota: 5H:100%/W:100%)

Account rotated on disk. The new account will be used on the next session.
Run /compact now if you want to restart immediately with the new account.
```
