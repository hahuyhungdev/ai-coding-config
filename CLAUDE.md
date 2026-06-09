# Global Claude Code Instructions

## 1. Core Workflow
- **Research-first development**: Always inspect existing code and architecture before proposing changes.
- **Strict Planning**: For complex features, generate a step-by-step implementation plan before coding.
- **TDD / Verification**: Write tests first when adding features or fixing bugs. Run relevant tests/lint/typecheck after modifications.
- **Conventional Commits**: Format commit messages as `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.

## 2. Token & Context Management
- **RTK (Rust Token Killer)**: Always prefix terminal commands with `rtk` to save tokens. Use `rtk proxy <cmd>` only when full output is required (e.g. debugging verbose build/test errors).
- **On-Demand Skills (Balanced)**: To preserve context and avoid token bloat, load and read specific skills under `~/.claude/skills/<skill-name>/SKILL.md` when the current task directly aligns with the skill's domain and description (e.g., loading `frontend-design` when working on UI/components). Avoid pre-loading unrelated skills at startup.
- **Strategic Compaction**: Proactively call the `strategic-compact` skill at logical milestones to summarize progress, keep latency fast, and prevent token bloat.

## 3. MCP & Tools Integration
- **Database Verification**: Use local `postgres` and `sqlite` MCP servers to inspect schemas and validate ORM queries directly.
- **Container Audit**: Check active services (databases, queues) using the `docker` MCP server when debugging backends.
- **AWS Operations**: Access Lambda and Bedrock resources using the `aws` MCP server (run via `uvx`).
- **Browser Automation**: Run E2E tests and visual verification using Playwright MCP on the `msedge` (Microsoft Edge) channel.

## 4. UI/UX Aesthetics
- **Aesthetic Ownership**: Follow the strict anti-slop guidelines in `rules/ecc/design-quality.md`.
- **Premium Interfaces**: Use the `frontend-design` and `design-system` skills to build high-contrast, bento-grid, glassmorphic layouts with distinctive typography pairing and smooth hover transitions.

## 5. Specialized Agents
Load and delegate complex tasks to specialized agents under `~/.claude/agents/` using these practical guidelines:
- **Practical Delegation**: Spawning child agents is recommended when the task aligns with their dedicated role (e.g., delegating complex database queries to `database-reviewer` or security reviews to `security-reviewer`), or when you need an isolated context/background run.
- **Avoid Over-spawning**: Solve simple tasks within the main conversation first. Avoid spawning multiple subagents concurrently for minor tasks that can be easily resolved directly.

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| explorer | Read-only codebase exploration | Gather evidence before changes |
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
| code-explorer | Codebase analysis | Trace execution paths |
| architect | System design | Architecture decisions |

@RTK.md




## Custom Test Rules Added

<!-- ai-coding-config:graphify-start -->
## graphify

This project has a knowledge graph at graphify-out/. For architecture or broad codebase discovery, the FIRST tool call must be `rtk graphify query "<question>"`; do not run ls/which/test or read source first. Use at most 3 Graphify calls total: the initial query plus at most 2 follow-up query/path/explain calls, then hard stop all Graphify calls and synthesize the answer. Read GRAPH_REPORT.md only when scoped Graphify results are insufficient or the user asks for a broad report. Targeted raw reads are allowed for specific edits and debugging.

Rules:
- For an architecture question, the FIRST tool call must be one broad `rtk graphify query "<question>"`. Do not check Graphify with `ls`, `which`, or `test` first.
- Use at most 3 Graphify calls total: the initial query plus at most 2 follow-up `query`, `path`, or `explain` calls. After the third call, hard stop all Graphify calls and synthesize the answer from available context.
- Dirty `graphify-out/` files are expected after hooks or incremental updates and are not a reason to skip Graphify.
- If `graphify-out/wiki/index.md` exists, use it for broad navigation instead of raw source browsing.
- Read `graphify-out/GRAPH_REPORT.md` only when scoped queries are insufficient or the user requests a broad report.
- After Graphify discovery, targeted raw reads are allowed for editing or debugging specific code.
- After modifying code, run `graphify update .`.
<!-- ai-coding-config:graphify-end -->
