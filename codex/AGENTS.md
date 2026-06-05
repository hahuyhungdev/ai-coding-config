# ECC for Codex CLI

## 1. Core Workflow
- **Research-first development**: Always inspect existing code and architecture before proposing changes.
- **Strict Planning**: For complex features, generate a step-by-step implementation plan before coding.
- **TDD / Verification**: Write tests first when adding features or fixing bugs. Run relevant tests/lint/typecheck after modifications.
- **Conventional Commits**: Format commit messages as `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.

## 2. Token & Context Management
- **RTK (Rust Token Killer)**: Always prefix terminal commands with `rtk` to save tokens. Use `rtk proxy <cmd>` only when full output is required (e.g. debugging verbose build/test errors). See `~/.codex/RTK.md` for reference.
- **Lazy-Load Skills on Description Match**: Never read or load a skill's `SKILL.md` at the beginning of a session. Only load and read a specific skill under `~/.codex/skills/<skill-name>/SKILL.md` when the current task directly matches the skill's domain and description (e.g., loading `frontend-design` only when modifying UI/components). Limit to at most 1-2 relevant skills per task to prevent token bloat and avoid arbitrary loading.
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
Load and delegate complex tasks to specialized agents under `~/.codex/agents/` using the `/agent` command strictly following these lazy-loading and anti-abuse best practices:
- **Spawning Triggers**: Do not spawn or call subagents for simple tasks. Only invoke a specialized agent when the task complexity requires it and matches the agent's specific description/role.
- **Parent-First Policy**: Solve tasks yourself (the parent agent) by default. Only delegate to a subagent when:
  1. A background task is long-running and you need to continue working.
  2. The task requires highly specialized domain knowledge (e.g., security audits or complex SQL optimization) matching the agent's description.
  3. The task requires a fresh context to avoid cluttering the parent conversation.
- **No Fanout Abuse**: Never spawn multiple subagents concurrently or in a loop unless explicitly requested by the user.

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


