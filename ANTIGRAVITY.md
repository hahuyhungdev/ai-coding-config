<!-- ai-coding-config:graphify-start -->
## graphify

⚠️ GRAPHIFY WORKFLOW RULES:
CRITICAL: For any codebase structure/relationship questions, your FIRST tool call MUST be `rtk graphify query "<question>"`. Graphify-first is mandatory.

Rules:
- For codebase exploration, use **Graphify-only**. Do NOT use view_file, list_dir, cat, grep, or inline scripts to explore.
- Use at most **20 Graphify calls** per question. After 20 calls, hard stop and synthesize.
- After Graphify discovery, targeted raw reads ARE allowed for: **editing**, **debugging**, and **config review** of specific files identified by Graphify.
- Read `graphify-out/GRAPH_REPORT.md` only when scoped queries are insufficient or a broad report is requested.
- If a tool is blocked, do not retry. Run `graphify update .` after code edits.
<!-- ai-coding-config:graphify-end -->
