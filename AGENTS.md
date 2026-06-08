# ECC for Codex CLI

## 1. Core Workflow
- **Research-first development**: Always inspect existing code and architecture before proposing changes.
- **Strict Planning**: For complex features, generate a step-by-step implementation plan before coding.
- **TDD / Verification**: Write tests first when adding features or fixing bugs. Run relevant tests/lint/typecheck after modifications.
- **Conventional Commits**: Format commit messages as `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.

## 2. Token & Context Management
- **RTK (Rust Token Killer)**: Always prefix terminal commands with `rtk` to save tokens. Use `rtk proxy <cmd>` only when full output is required (e.g. debugging verbose build/test errors). See `~/.codex/RTK.md` for reference.
- **On-Demand Skills (Balanced)**: To preserve context and avoid token bloat, load and read specific skills under `~/.codex/skills/<skill-name>/SKILL.md` when the current task directly aligns with the skill's domain and description (e.g., loading `frontend-design` when working on UI/components). Avoid pre-loading unrelated skills at startup.
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
Load and delegate complex tasks to specialized agents under `~/.codex/agents/` using the `/agent` command with these practical guidelines:
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

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
