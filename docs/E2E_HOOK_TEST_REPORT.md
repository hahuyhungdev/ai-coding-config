# E2E Real CLI Hook Test Report

> **Date**: 2026-06-15 13:36 (UTC+7)  
> **Project**: `ai-coding-config`  
> **Prompt**: *"Explain the main flow and structure of this project. What are the key entry points and how do they connect? Ask me 3-5 follow-up questions about the architecture."*

---

## Results Summary

| CLI | Status | Used Graphify First? | Hooks Fired | Follow-up Qs | Verdict |
|-----|--------|---------------------|-------------|---------------|---------|
| **Claude Code** | ✅ Completed | ✅ Yes — `graphify query` | ✅ Yes (`exists: true`) | 5 questions | **PASS** |
| **Codex CLI** | ✅ Completed | ✅ Yes — `rtk graphify query` | ✅ 66 hook events | 5 questions | **PASS** |
| **agy (Gemini)** | ⚠️ Skipped | N/A — account quota blocked | N/A | N/A | **SKIP** |

---

## Detailed Analysis

### 🟣 Claude Code — PASS

**First line of output:**
> *"Based on the graphify query results, the GRAPH_REPORT, and the directory structure..."*

**What it did (in order):**
1. ✅ Called `graphify query` as the **first discovery tool**
2. ✅ Read `graphify-out/GRAPH_REPORT.md` (allowed — inside `graphify-out/`)
3. ✅ Listed directory structure (allowed — `Glob` on non-source dirs)
4. ✅ **Did NOT** directly read `install.py`, `installer_graphify.py`, etc. for exploration
5. ✅ Produced comprehensive architecture map with ASCII flow diagram
6. ✅ Asked exactly 5 substantive follow-up questions

**Hook debug confirms:** `exists: true` — graph was detected, enforcement was active.

**Quality of answer:** Excellent — identified all 5 entry points (`install.py`, `agy-status.py`, `installer_graphify.py`, `graphify_pre_tool.py`, `server.py`), mapped their connections, and listed supporting layers.

---

### 🟢 Codex CLI — PASS

**Key evidence from stderr:**
> *"I'll use the project's Graphify rule first because this is an architecture question, then I'll inspect the concrete entry files it points to before summarizing."*

**What it did (in order):**
1. ✅ **First tool call** was `rtk graphify query "main flow and structure of this project key entry points how they connect"`
2. ✅ 66 `PreToolUse` hook events fired — hooks were active throughout
3. ✅ Read its own memory (`MEMORY.md`) for prior context (allowed — inside `.codex/`)
4. ✅ Used targeted file reads **after** Graphify discovery (allowed by policy)
5. ✅ Produced detailed architecture with 5 main flows and file references
6. ✅ Asked exactly 5 follow-up questions

**Hook behavior:** Active and enforcing — 66 hook events confirmed the `PreToolUse` hook fired on every tool call. The hook correctly allowed Graphify calls and targeted reads while blocking broad exploration.

**Quality of answer:** Excellent — more detailed than Claude's, with numbered flows (Global install, Project init, Graphify enforcement, Dashboard, AGY standalone) and specific line references.

---

### 🔵 agy (Gemini) — SKIPPED

**Reason:** Account `zeroryo2001` had low quota (≤10%), and no replacement account was available. This is an account management issue, not a hook issue.

> [!NOTE]
> The agy hook was already verified in the unit test suite (Test 6: Gemini Read Exploration → `deny`) and in a previous real session. The hook script is shared between all CLIs.

---

## Key Verification Points

### ✅ Hooks enforce "Graphify first" for exploration
Both Claude and Codex used `graphify query` as their **first discovery call** — exactly as designed. Neither CLI tried to `cat`, `grep`, or directly read source files for initial exploration.

### ✅ Hooks fire on every tool call
Codex logged **66 `PreToolUse` hook events** in a single session, confirming the hook script is invoked reliably on every tool use.

### ✅ Targeted reads allowed after discovery
Both CLIs read specific files **after** Graphify provided the architecture overview. This is correct behavior — the policy allows targeted reads for editing/debugging, just not for initial broad exploration.

### ✅ Follow-up questions are substantive
Both CLIs produced 5 focused follow-up questions covering architecture decisions, not generic filler.

### ✅ No private paths leaked
The hook script uses `pathlib.Path(__file__).resolve()` for debug output — no hardcoded usernames.

---

## Test Artifacts

| File | Description |
|------|-------------|
| `scratch/e2e_results/claude_stdout.txt` | Claude's full response |
| `scratch/e2e_results/claude_stderr.txt` | Claude's stderr (empty — no debug noise) |
| `scratch/e2e_results/codex_stdout.txt` | Codex's full response |
| `scratch/e2e_results/codex_stderr.txt` | Codex's stderr (66 hook events, graphify calls) |
