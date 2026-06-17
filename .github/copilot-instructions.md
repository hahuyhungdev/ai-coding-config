# Global Copilot Instructions for ECC

## 1. Core Workflow
- **Research-first development**: Always inspect existing code and architecture before proposing changes.
- **Strict Planning**: For complex features, generate a step-by-step implementation plan before coding.
- **TDD / Verification**: Write tests first when adding features or fixing bugs. Run relevant tests/lint/typecheck after modifications.
- **Conventional Commits**: Format commit messages as `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.

## 2. Token & Context Management
- **RTK (Rust Token Killer)**: Always prefix terminal commands with `rtk` to save tokens. Use `rtk proxy <cmd>` only when full output is required (e.g. debugging verbose build/test errors).
- **On-Demand Skills (Balanced)**: To preserve context and avoid token bloat, load and read specific skills under `~/.claude/skills/<skill-name>/SKILL.md` (or `~/.codex/skills/`) when the current task directly aligns with the skill's domain and description (e.g., loading `frontend-design` when working on UI/components). Avoid pre-loading unrelated skills at startup.
- **Strategic Compaction**: Proactively call the `compact` skill at logical milestones to summarize progress, keep latency fast, and prevent token bloat.

## 3. MCP & Tools Integration
- **Database Verification**: Use local `postgres` and `sqlite` MCP servers to inspect schemas and validate ORM queries directly.
- **Container Audit**: Check active services (databases, queues) using the `docker` MCP server when debugging backends.
- **AWS Operations**: Access Lambda and Bedrock resources using the `aws` MCP server (run via `uvx`).
- **Browser Automation**: Run E2E tests and visual verification using Playwright MCP on the `msedge` (Microsoft Edge) channel.

## 4. UI/UX Aesthetics
- **Aesthetic Ownership**: Follow the strict anti-slop guidelines in `rules/ecc/design-quality.md`.
- **Premium Interfaces**: Use clean, modern high-contrast design systems (e.g., bento-grid, glassmorphism, responsive layouts) with distinct, clean typography.

## 5. Specialized Agents
Load and delegate complex tasks to specialized agents under `~/.claude/agents/` (or `~/.codex/agents/`) using the `/agent` command with these practical guidelines:
- **Practical Delegation**: Spawning child agents is recommended when the task aligns with their dedicated role (e.g., delegating complex database queries to `database-reviewer` or security reviews to `security-reviewer`), or when you need an isolated context/background run.
- **Avoid Over-spawning**: Solve simple tasks within the main conversation first. Avoid spawning multiple subagents concurrently for minor tasks that can be easily resolved directly.

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| reviewer | PR review (correctness + security) | After writing code |
| docs-researcher | API/docs verification | Before implementing APIs |
| planner | Implementation planning | Complex features, refactoring |
| code-reviewer | Code quality review | After writing code |
| security-reviewer | Security analysis | Auth, user input, API endpoints |
| build-error-resolver | Fix build/type errors | When build fails |
| tdd-guide | Test-driven development | New features, bug fixes |
| typescript-reviewer | TypeScript/JS review | All TS/JS changes |
| database-reviewer | PostgreSQL specialist | Schema changes, query optimization |
| e2e-runner | Playwright E2E testing | Critical user flows |
| performance-optimizer | Performance analysis | Slow code, bundle size |
| refactor-cleaner | Dead code cleanup | Code maintenance |
| architect | System design | Architecture decisions |

## 6. Graphify — Knowledge Graph Navigation

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
