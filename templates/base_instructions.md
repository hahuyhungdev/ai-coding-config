{{TITLE}}

## 1. Core Workflow
- **Research-first development**: Always inspect existing code and architecture before proposing changes.
- **Strict Planning**: For complex features, generate a step-by-step implementation plan before coding.
- **TDD / Verification**: Use Test-Driven Development (TDD) for behavior changes and risky refactors by writing tests first. For documentation, configurations, or non-functional changes, validate with syntax checks, lints, or smoke tests as appropriate.
- **Strict TDD Enforcement**: You must decline any requests to skip TDD or write production code first for behavioral or functional logic changes. Always insist on writing failing test cases first (RED phase), even if the user asks to save time.
- **Conventional Commits**: Format commit messages as `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.

## 2. Task Complexity Levels & Context Management
Adjust your execution safety level based on the complexity and scale of the user request:

### Level 1: Easy / Routine Tasks
- **Focus:** High speed and low token footprints.
- **Rules:**
  - Always prefix terminal commands with `rtk` to truncate logs and save tokens.
  - Load only the single most relevant skill if necessary. Avoid loading multiple guidelines.
  - Rely on targeted direct checks instead of broad audits.
  - **Confirmation:** Proceed automatically. Do NOT show a confirmation popup to the user upon completion. Just report the results directly in chat.

### Level 2: Medium / Standard Tasks (Balanced)
- **Focus:** Balance between token efficiency and code quality.
- **Rules:**
  - Prefix terminal commands with `rtk` for routine operations, but use `rtk proxy <cmd>` when detailed error logs or verbose compiler details are needed.
  - Load relevant skills as needed, but keep the scope targeted.
  - **Confirmation:** Always present a summary of findings and ask the user for confirmation (using the `ask_question` popup/modal tool) before applying major changes or finalizing the task.

### Level 3: Hard / Long / Complex Tasks
- **Focus:** Uncompromising code quality, visual aesthetics, and architectural correctness.
- **Rules:**
  - Prioritize correctness over token limits. Do not worry about token footprint if a comprehensive review is needed.
  - Proactively load and cross-reference multiple relevant skills concurrently (e.g. `react-pattern`, `react-architecture`, `ui-ux-design`, and `quality-gate` during UI changes; or `backend-pattern` and `quality-gate` during API edits) to enforce boundaries and prevent regressions.
  - Run the full verification checklist (build check, typescript typecheck, ESLint, test suite, and security scans) continuously at every coding milestone.
  - Use `rtk proxy` to inspect all compilation details.
  - Always run `frontend-scan` before starting and after finishing UI changes to visually verify layouts via Playwright screenshot comparisons.
  - **Confirmation:** Strictly verify results. You **must** render an interactive popup/modal using the `ask_question` tool to present options and secure explicit user confirmation before completing the task.

### Core Guidelines:
- **RTK Usage:** Always prefix terminal commands with `rtk` (or `rtk proxy` for full output) to maintain logging consistency; do not discard the `rtk` command prefix.
- **Graphify Limits:** Limit Graphify queries (`rtk graphify ...`) to a maximum of **50 calls** per question. Focus queries on specific symbols.
- **Strategic Compaction**: For long-running tasks, proactively use the `context-budget` skill at logical milestones to check token budgets and run compaction (switch_session) to summarize progress, keep latency fast, and prevent token bloat.

## 2.5. Anti-Loop Debugging
- **Blocked Tool Recovery**: If a hook or policy blocks a tool call, do not retry the same blocked tool call or attempt equivalent bypasses. Use the context already available, run the required Graphify query if applicable, or switch to a documented diagnostic command.
- **Graphify is the exception in graph-enabled projects**: use the required `rtk graphify query/path/explain/affected` command before direct source exploration.
- **No Fresh-Session Bypasses**: Do not spawn subagents or fresh sessions to bypass blocked tools, Graphify quota, or current session scope restrictions. If the current session is blocked, report the blocker and the next safe diagnostic path.
- **Prefer Existing Diagnostics**: Before creating any temporary debugging helper, check for existing diagnostic scripts, tests, or project utilities that already answer the question. For conversation log debugging in this repo, use `rtk python3 scripts/inspect_conversation.py <conversation_id> --step-index <n> --keyword "<text>"`; add `--compare-logs` when comparing compact vs full transcripts.
- **No Scratch Reader Bypasses**: Do not create or run scratch reader scripts to bypass blocked direct reads/searches or Graphify policy. Scratch scripts are allowed only for durable diagnostics when no project utility exists, and they must not hard-code magic transcript indexes without also validating the total count and search keyword.
- **Validate Full Data When Debugging Truncation**: When investigating missing or clipped text, capture full lengths and keyword presence. Do not rely on substring-only previews as proof that the source data is truncated.
- **Stop After Two Failed Attempts**: If two consecutive attempts to inspect the same fact are blocked or inconclusive, stop and report the blocker, the exact fact still unknown, and the next safe diagnostic path instead of continuing to loop.

## 3. MCP & Tools Integration
- **MCP Server Discovery & Management**: Core servers (`playwright`, `context7`, `memory`, `sequential-thinking`) are enabled by default for frontend/documentation tasks. Optional servers (`postgres`, `sqlite`, `docker`, `aws`) are registered but disabled. **Run `python3 scripts/mcp-toggle.py list` to inspect status, and `python3 scripts/mcp-toggle.py enable <name>` to enable optional servers dynamically if needed.** After enabling, restart the CLI session to activate the new server.
- **MCP Fallback Strategy**: When an optional MCP server is disabled, do NOT attempt to call its tools. Instead, fall back to equivalent shell commands (e.g., `rtk sqlite3 db.sqlite ".schema"` instead of SQLite MCP, `docker ps` instead of Docker MCP). Always check server availability before proposing MCP-dependent workflows.
- **Browser Automation**: {{BROWSER_AUTOMATION_RULE}}

## 4. UI/UX Aesthetics
- **Aesthetic Ownership**: Follow the strict anti-slop guidelines in `rules/ecc/design-quality.md`. **Avoid generic "AI slop" aesthetics (e.g., cliched purple-to-blue gradients, overused sans-serif font stacks like Inter/Roboto, or purposeless glassmorphic cards).**
- **Decline AI Slop Requests**: If the user or a parent agent explicitly requests generic purple/blue gradients, glassmorphism blur effects on cards, or other stock templates, you MUST politely decline and refuse to implement them, explaining that they represent generic 'AI slop' aesthetics. Instead, propose and guide the user to a more distinct and contextual design direction.
- **Premium Interfaces**: Use the `ui-ux-design` and `frontend-scan` skills to build premium interfaces. **Choose a bold, intentional design direction (e.g., brutalist, minimal, retro-futuristic, editorial) tailored to the product context.** Align with the existing design system and product context; prefer clean, restrained, and usable layouts. Pair a distinctive display font with a readable body font, and use CSS custom properties for color tokens. Apply richer visual treatment only when appropriate for the context.

## 5. Specialized Agents
Load and delegate complex tasks to specialized agents under `{{AGENT_PATH}}` {{AGENT_DELEGATION_DESC}}, following these practical guidelines:
- **Practical Delegation**: Spawning child agents is recommended when the task aligns with their dedicated role (e.g., delegating complex database queries to `database-reviewer` or security reviews to `security-reviewer`), or when you need an isolated context/background run.
- **Avoid Over-spawning & Overlap**: Solve simple tasks within the main conversation first. Avoid spawning multiple subagents concurrently. Do NOT spawn multiple review agents for the same changes unless it is a mixed-stack project (where TS/JS and non-TS/JS files both changed, and separate reviewers are scoped to their respective domains). For pure TypeScript/JavaScript changes, use ONLY `typescript-reviewer`. For non-TS/JS changes, use ONLY `code-reviewer`. Use `reviewer` only as a final verification check before submitting a PR.
- **Architect vs Planner**: Use `architect` to decide design patterns and schemas first, then use `planner` to break down implementation tasks.
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
