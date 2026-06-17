

<!-- ai-coding-config:graphify-start -->
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
- Use at most **10 Graphify calls** total per question. After 10 calls, hard stop and synthesize from available context.
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
<!-- ai-coding-config:graphify-end -->
