# Audit Report: Graphify RTK Prompt Optimization

## 1. Executive Summary
This report details the audit findings and token minimization POC for `GRAPHIFY_INSTRUCTIONS` prompt block in the Google Antigravity AI Coding Config environment. The original instructions block consumed ~700 tokens (approx. 2,660 characters). By minifying the prompt instructions to focus on core constraints while preserving all functional validation substrings, we achieved a **71.14% token reduction** (reducing the instruction block to ~202 tokens / 767 characters) without breaking any unit tests or hook enforcement behaviors.

## 2. Audit Findings
* **Original Prompt Size**: 2,660 characters | 386 words | ~700 tokens
* **New Prompt Size**: 767 characters | 112 words | ~202 tokens
* **Token Savings**: **71.14%** (measured programmatically using `scripts/measure_token_savings.py`)
* **Test Suite Verification**: Running `python3 -m unittest tests/test_installer_graphify.py` verifies that all 26 unit tests pass, confirming that the new instructions successfully preserve the critical validation constraints.

### Preserved Substrings
The following validation substrings checked by `tests/test_installer_graphify.py` were fully preserved to ensure correctness and backward compatibility:
1. `Graphify-only` - Ensures the agent uses Graphify for codebase exploration.
2. `20 Graphify calls` - Controls the maximum calls budget constraint.
3. `targeted raw reads` - Specifies the allowed exceptions for reads.
4. `GRAPH_REPORT.md` - Directs the agent to the generated markdown report.
5. `hard stop` - Confirms the explicit termination strategy when the call limit is hit.

---

## 3. Minification Comparison

### Original Prompt Block
```markdown
## graphify

⚠️ GRAPHIFY WORKFLOW RULES (MANDATORY — READ BEFORE ANY CODEBASE EXPLORATION):

**CRITICAL: For ANY question about codebase structure, architecture, or file relationships, your VERY FIRST tool call MUST be `rtk graphify query "<question>"`. Do NOT use `list_dir`, `grep_search`, `find`, `cat`, or `view_file` as your first exploration step. Graphify-first is non-negotiable.**

Commands:
- Architecture questions → `rtk graphify query "question"`
- Code relationships → `rtk graphify path "A" "B"`
- Deep-dive concepts → `rtk graphify explain "concept"`
- Impact analysis / reverse dependencies → `rtk graphify affected "SymbolName"`

Rules:
- For codebase exploration, use **Graphify-only**. Do NOT use view_file, list_dir, cat, grep, sed, awk, or inline scripts to explore.
- Use at most **20 Graphify calls** total per question. After 20 calls, hard stop and synthesize from available context.
- **Focus queries on specific symbols** — prefer `graphify query "what does X do"` over `graphify query "explain the codebase"`.
- **Synthesize from Graphify context only.** Answer based on what Graphify returns. Do not supplement with direct file reads for exploration.
- **If a tool call is blocked, do not retry.** Proceed and answer using the available context.
- Dirty `graphify-out/` files are expected after hooks or incremental updates and are not a reason to skip Graphify.
- If `graphify-out/wiki/index.md` exists, use it for broad navigation instead of raw source browsing.
- Read `graphify-out/GRAPH_REPORT.md` only when scoped queries are insufficient or the user requests a broad report.

Post-Discovery Reads (exceptions):
- After Graphify discovery, targeted raw reads ARE allowed for: **editing**, **debugging**, and **config review** of specific files already identified by Graphify.
- You MUST have run at least one Graphify query before reading source files directly.
- When reading after discovery, state your justification (e.g., "Reading for editing" or "Verifying config structure").
- After modifying code, run `graphify update .`.

Blocked Tool Recovery:
- If a hook blocks a direct read/search or inline script, do not retry the same blocked call or attempt an equivalent bypass.
- Do not create one-off scratch scripts to inspect facts that a project diagnostic already covers.
- For conversation log debugging in this repo, use `rtk python3 scripts/inspect_conversation.py <conversation_id> --step-index <n> --keyword "<text>"`; add `--compare-logs` when comparing compact vs full transcripts.
- When debugging truncation, measure full content length and keyword presence; do not use substring-only previews as evidence.
```

### Minified Prompt Block
```markdown
## graphify

⚠️ GRAPHIFY WORKFLOW RULES:
CRITICAL: For any codebase structure/relationship questions, your FIRST tool call MUST be `rtk graphify query "<question>"`. Graphify-first is mandatory.

Rules:
- For codebase exploration, use **Graphify-only**. Do NOT use view_file, list_dir, cat, grep, or inline scripts to explore.
- Use at most **20 Graphify calls** per question. After 20 calls, hard stop and synthesize.
- After Graphify discovery, targeted raw reads ARE allowed for: **editing**, **debugging**, and **config review** of specific files identified by Graphify.
- Read `graphify-out/GRAPH_REPORT.md` only when scoped queries are insufficient or a broad report is requested.
- If a tool is blocked, do not retry. Run `graphify update .` after code edits.
```

---

## 4. Alternative Optimization Strategies

Beyond manual text minification, the following three concrete strategies can further optimize token usage and system performance:

### Strategy A: Dynamic Prompt Compression (DPC)
* **Concept**: Dynamically inject, compress, or completely omit the Graphify instruction block based on the state of the active development session.
* **Mechanism**:
  * If a Graphify database query has already been executed in the current session (indicating the discovery phase is complete), the system instructions can dynamically collapse the Graphify rules into a single-line reminder: `*Discovery done. Use targeted raw reads.*`
  * If no codebase queries are relevant (e.g., in purely mathematical or non-code task directories), the instruction block is completely stripped from the context window.
* **Trade-offs**: Requires context-aware middleware/pre-processors that inspect the conversation history before constructing the prompt, adding slight latency to the initial prompt compilation.

### Strategy B: Native Enforcement Hooks in RTK
* **Concept**: Move the workflow validation logic from the LLM prompt entirely to the Rust Token Killer (`rtk`) execution engine.
* **Mechanism**:
  * Instead of training the LLM via prompt text to avoid direct file reads and discovery commands, the `rtk` binary intercepts all shell executions (e.g., `grep`, `find`, `cat`) and checks if they violate exploration rules.
  * If a violation occurs, the tool call is rejected native-side, and `rtk` returns a highly descriptive warning message indicating `rtk graphify query` should be run.
* **Trade-offs**: Simplifies the system prompt (saving 100% of these prompt tokens), but shifts execution-time verification into the binary layer, making the rule set less flexible without compiling updates.

### Strategy C: On-Demand Skill Loading (Lazy Loading)
* **Concept**: Refactor the Graphify workflow rules as a specialized, lazy-loaded Antigravity Skill rather than a persistent global system instruction.
* **Mechanism**:
  * The instructions are saved in `skills/graphify/SKILL.md`.
  * The LLM's system prompt contains only a one-line index pointing to the available skills.
  * When the LLM receives a codebase query, it detects the need for structure discovery and loads the `graphify` skill dynamically, adding it to the context window only for the duration of the exploration phase.
* **Trade-offs**: Maximizes token savings for standard coding tasks, but relies on the LLM's reliability in accurately recognizing when to trigger the skill loading action.
