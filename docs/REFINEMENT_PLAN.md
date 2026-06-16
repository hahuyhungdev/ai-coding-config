# Refinement Plan — Post-Measurement

> Based on empirical data from Sessions A–D.

## Key Insight

> [!IMPORTANT]
> **Prompt specificity is the biggest lever.** Session D (symbol-focused, strict instructions) had **0 blocks, 0 bypass attempts** — the AI never even tried to lách luật. Hard blocks are a safety net, not the primary control.

---

## Track 1: Fix Remaining Bypass Gaps (Hook)

### 1.1 Add `ls` to blocked discovery commands
`ls` is currently **allowed**, but Session C shows AI uses it for exploration (`ls -la .git/hooks`, `ls src/`).

**Files**: `graphify_pre_tool.py` (B tuple), `installer_graphify.py` (BROAD_DISCOVERY_COMMANDS)

```diff
# graphify_pre_tool.py
 B = (
-    'ack', 'ag', 'awk', 'bat', 'cat', 'diff', 'fd', 'find', 'grep', 'head', 'hexdump',
+    'ack', 'ag', 'awk', 'bat', 'cat', 'diff', 'fd', 'find', 'grep', 'head', 'hexdump',
+    'ls',
     ...
 )
```

> [!WARNING]
> Adding `ls` will break the existing test `test_normal_test_ls_and_which_commands_are_allowed` which expects `ls config` to pass. Need to update test expectations.

### 1.2 Expand inline script detection keywords
Currently checks for `("open", "read", "load", "file")` keywords. Session C shows AI uses:
- `os.listdir('.')`
- `os.walk(...)`

**Fix**: Add directory traversal keywords to the read detection:
```python
has_read_keyword = any(kw in lowered for kw in (
    "open", "read", "load", "file",
    "listdir", "scandir", "walk", "glob",   # <-- NEW
))
```

### 1.3 Update tests
- Move `"ls config"` from allowed → blocked in tests
- Add `os.listdir` and `os.walk` inline Python bypass test cases

---

## Track 2: Encode Session D Pattern into Default Instructions (Biggest Impact)

### 2.1 The Problem
Current instructions in `AGENTS.md` / `CLAUDE.md` say:
```
For ANY question about codebase structure, your VERY FIRST tool call
MUST be `rtk graphify query "<question>"`.
```

This is **broad** — it tells the AI _what tool to use first_, but doesn't tell it _how to stay disciplined after_. Session C proves that after the first Graphify call, the AI reverts to direct reads.

### 2.2 The Session D Pattern (Proven Best)
```
Use Graphify-only; no view_file/list_dir/cat/grep/python file reads.
Use at most 3 Graphify calls.
Focus your Graphify queries on: <specific symbols>.
Answer from Graphify context only.
If blocked, do not retry blocked calls.
```

### 2.3 Proposed Instruction Update
Update the `GRAPHIFY_INSTRUCTIONS` block in `installer_graphify.py` and `AGENTS.md` to encode the Session D behavioral rules:

```markdown
## Graphify Workflow

Rules:
1. Use **Graphify-only** for codebase exploration. Do NOT use
   view_file, list_dir, cat, grep, sed, awk, or inline scripts
   to explore the codebase.
2. Use at most **3 Graphify calls** total per question.
3. **Focus queries on specific symbols** — prefer
   `graphify query "what does _command_words do"` over
   `graphify query "explain the codebase"`.
4. **Synthesize from Graphify context only.** After your queries,
   compose the answer from what Graphify returned. Do not
   supplement with direct file reads.
5. **If a tool call is blocked, do not retry.** Move on and
   synthesize from available context.

Post-Discovery Reads (exceptions):
- Targeted reads ARE allowed for **editing**, **debugging**, and
  **config review** of specific files already identified by Graphify.
- State your justification before reading (e.g., "Reading for editing").
```

> [!TIP]
> The key difference from current instructions: explicitly saying **"answer from Graphify context only"** and **"do not retry blocked calls"**. These two rules are what made Session D work perfectly.

---

## Track 3: Blocker Message Improvement (Quick Win)

Current blocker messages say _what was blocked_ but don't guide the AI to the right behavior. Improve them to reduce retry attempts:

```diff
- "❌ BLOCKED: Search tools are blocked for codebase exploration!"
+ "❌ BLOCKED: Direct search/read tools are not available for exploration.
+  Answer from your existing Graphify context. Do NOT retry this call
+  or attempt alternative read methods — they will also be blocked."
```

---

## Execution Order

| Priority | Track | Effort | Impact |
|----------|-------|--------|--------|
| 1 | Track 2 — Instruction update | Low | **Highest** (Session D proves it) |
| 2 | Track 3 — Blocker message improvement | Low | Medium (reduces retry spam) |
| 3 | Track 1 — Bypass gap fixes | Medium | Low-Medium (safety net) |

> [!NOTE]
> Track 2 should be done first because it addresses the root cause (AI behavior) rather than symptoms (bypass attempts). Track 1 is still valuable as defense-in-depth.
