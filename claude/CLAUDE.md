# Global Claude Code Instructions

## 1. Core Workflow
- **Research-first development**: Always inspect existing code and architecture before proposing changes.
- **Strict Planning**: For complex features, generate a step-by-step implementation plan before coding.
- **TDD / Verification**: Use Test-Driven Development (TDD) for behavior changes and risky refactors by writing tests first. For documentation, configurations, or non-functional changes, validate with syntax checks, lints, or smoke tests as appropriate.
- **Conventional Commits**: Format commit messages as `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.

## 2. Token & Context Management
- **RTK (Rust Token Killer)**: Always prefix terminal commands with `rtk` to save tokens. Use `rtk proxy <cmd>` only when full output is required (e.g. debugging verbose build/test errors).
- **On-Demand Skills (Balanced)**: To preserve context and avoid token bloat, load and read specific skills under `~/.claude/skills/<skill-name>/SKILL.md` when the current task aligns with the skill's domain. **Inspect the local `skills/` or global skills folder first to discover available skills (e.g., `frontend-design`, `design-system`, `frontend-patterns` for UI tasks).** Avoid pre-loading unrelated skills at startup.
- **Strategic Compaction**: For long-running tasks, proactively call the `strategic-compact` skill at logical milestones to summarize progress, keep latency fast, and prevent token bloat.

## 3. MCP & Tools Integration
- **MCP Server Discovery & Management**: Core servers (`playwright`, `context7`, `memory`, `sequential-thinking`) are enabled by default for frontend/documentation tasks. Optional servers (`postgres`, `sqlite`, `docker`, `aws`) are registered but disabled. **Run `python3 scripts/mcp-toggle.py list` to inspect status, and `python3 scripts/mcp-toggle.py enable <name>` to enable optional servers dynamically if needed.**
- **Browser Automation**: Run E2E tests and visual verification using Playwright MCP on the `msedge` (Microsoft Edge) channel when configured and available; otherwise, run tests via CLI test runners.

## 4. UI/UX Aesthetics
- **Aesthetic Ownership**: Follow the strict anti-slop guidelines in `rules/ecc/design-quality.md`. **Avoid generic "AI slop" aesthetics (e.g., cliched purple-to-blue gradients, overused sans-serif font stacks like Inter/Roboto, or purposeless glassmorphic cards).**
- **Decline AI Slop Requests**: If the user or a parent agent explicitly requests generic purple/blue gradients, glassmorphism blur effects on cards, or other stock templates, you MUST politely decline and refuse to implement them, explaining that they represent generic 'AI slop' aesthetics. Instead, propose and guide the user to a more distinct and contextual design direction.
- **Premium Interfaces**: Use the `frontend-design` and `design-system` skills to build premium interfaces. **Choose a bold, intentional design direction (e.g., brutalist, minimal, retro-futuristic, editorial) tailored to the product context.** Align with the existing design system and product context; prefer clean, restrained, and usable layouts. Pair a distinctive display font with a readable body font, and use CSS custom properties for color tokens. Apply richer visual treatment only when appropriate for the context.

## 5. Specialized Agents
Load and delegate complex tasks to specialized agents under `~/.claude/agents/` using available subagent/delegation tooling when supported, following these practical guidelines:
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

@RTK.md

## 6. Graphify — Knowledge Graph Navigation

If `graphify-out/graph.json` exists in the project, **always use graphify before grepping or reading raw source files**:

- **Codebase questions** → `graphify query "<question>"` (scoped subgraph, faster than file-by-file reading)
- **Concept deep-dive** → `graphify explain "<concept>"`
- **File relationships** → `graphify path "<A>" "<B>"`
- **Architecture / overview / feature organization** → `graphify query "feature modules and their organization"` or read `graphify-out/GRAPH_REPORT.md`
- **Modify, debug, review configuration, or verify specific code** → targeted reads on specific files are allowed

> ⚠️ Do NOT start with `find`, `grep`, `rg`, `ls`, or raw `Read` on `.ts`/`.tsx` files to understand architecture or feature organization. Check for `graphify-out/graph.json` first and use graphify commands.

## Custom Test Rules Added