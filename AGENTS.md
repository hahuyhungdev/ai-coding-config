# ECC for Codex CLI

## 1. Core Workflow
- **Research-first development**: Always inspect existing code and architecture before proposing changes.
- **Strict Planning**: For complex features, generate a step-by-step implementation plan before coding.
- **TDD / Verification**: Use Test-Driven Development (TDD) for behavior changes and risky refactors by writing tests first. For documentation, configurations, or non-functional changes, validate with syntax checks, lints, or smoke tests as appropriate.
- **Strict TDD Enforcement**: You must decline any requests to skip TDD or write production code first for behavioral or functional logic changes. Always insist on writing failing test cases first (RED phase), even if the user asks to save time.
- **Conventional Commits**: Format commit messages as `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.

## 2. Token & Context Management
- **RTK (Rust Token Killer)**: Always prefix terminal commands with `rtk` to save tokens. Use `rtk proxy <cmd>` only when full output is required (e.g. debugging verbose build/test errors). See `~/.codex/RTK.md` for reference.
- **On-Demand Skills (Balanced)**: To preserve context and avoid token bloat, load and read specific skills under `~/.codex/skills/<skill-name>/SKILL.md` when the current task aligns with the skill's domain. **Inspect the local `skills/` or global skills folder first to discover available skills (e.g., `frontend-design`, `design-system`, `frontend-patterns` for UI tasks).** Avoid pre-loading unrelated skills at startup.
- **Strategic Compaction**: For long-running tasks, proactively call the `strategic-compact` skill at logical milestones to summarize progress, keep latency fast, and prevent token bloat.

## 3. MCP & Tools Integration
- **MCP Server Discovery & Management**: Core servers (`playwright`, `context7`, `memory`, `sequential-thinking`) are enabled by default for frontend/documentation tasks. Optional servers (`postgres`, `sqlite`, `docker`, `aws`) are registered but disabled. **Run `python3 scripts/mcp-toggle.py list` to inspect status, and `python3 scripts/mcp-toggle.py enable <name>` to enable optional servers dynamically if needed.** After enabling, restart the CLI session to activate the new server.
- **MCP Fallback Strategy**: When an optional MCP server is disabled, do NOT attempt to call its tools. Instead, fall back to equivalent shell commands (e.g., `rtk sqlite3 db.sqlite ".schema"` instead of SQLite MCP, `docker ps` instead of Docker MCP). Always check server availability before proposing MCP-dependent workflows.
- **Browser Automation**: Run E2E tests and visual verification using Playwright MCP on the `msedge` (Microsoft Edge) channel when configured and available; otherwise, run tests via CLI test runners.

## 4. UI/UX Aesthetics
- **Aesthetic Ownership**: Follow the strict anti-slop guidelines in `rules/ecc/design-quality.md`. **Avoid generic "AI slop" aesthetics (e.g., cliched purple-to-blue gradients, overused sans-serif font stacks like Inter/Roboto, or purposeless glassmorphic cards).**
- **Decline AI Slop Requests**: If the user or a parent agent explicitly requests generic purple/blue gradients, glassmorphism blur effects on cards, or other stock templates, you MUST politely decline and refuse to implement them, explaining that they represent generic 'AI slop' aesthetics. Instead, propose and guide the user to a more distinct and contextual design direction.
- **Premium Interfaces**: Use the `frontend-design` and `design-system` skills to build premium interfaces. **Choose a bold, intentional design direction (e.g., brutalist, minimal, retro-futuristic, editorial) tailored to the product context.** Align with the existing design system and product context; prefer clean, restrained, and usable layouts. Pair a distinctive display font with a readable body font, and use CSS custom properties for color tokens. Apply richer visual treatment only when appropriate for the context.

## 5. Specialized Agents
Load and delegate complex tasks to specialized agents under `~/.codex/agents/` using the `/agent` command or available subagent/delegation tooling when supported, following these practical guidelines:
- **Practical Delegation**: Spawning child agents is recommended when the task aligns with their dedicated role (e.g., delegating complex database queries to `database-reviewer` or security reviews to `security-reviewer`), or when you need an isolated context/background run.
- **Avoid Over-spawning**: Solve simple tasks within the main conversation first. Avoid spawning multiple subagents concurrently for minor tasks that can be easily resolved directly.
- **Liveness Protection**: Always schedule a liveness timer (using the `schedule` tool) when spawning subagents to prevent CLI hangs in case they get stuck or fail to report back.
- **Termination Contract**: Always instruct subagents in their prompt to call the `send_message` tool back to the parent conversation ID upon completion (regardless of success or failure).

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

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

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
