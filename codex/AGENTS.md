# ECC for Codex CLI

This supplements the root `AGENTS.md` with Codex-specific guidance.

## Model Recommendations

| Task Type | Recommended Model |
|-----------|------------------|
| All tasks | GPT 5.5 |

## Token Optimization (RTK)

Always prefix shell commands with `rtk` for token savings. See `~/.codex/RTK.md` for full reference.

```bash
rtk git status
rtk pnpm build
rtk pnpm test
rtk npx tsc --noEmit
```

Use `rtk proxy <cmd>` to bypass when full output is needed (debugging build failures, test output).

## Skills Discovery

Skills are loaded from `~/.codex/skills/`. Each skill contains:
- `SKILL.md` — Detailed instructions and workflow (loaded on-demand, not all at once)

## MCP Servers

Treat the project-local `.codex/config.toml` as the default Codex baseline for ECC.

## External Action Boundaries

Treat networked tools as read-only by default. Search, inspect, and draft freely within the user's requested scope, but require explicit user approval before posting, publishing, pushing, merging, opening paid jobs, dispatching remote agents, changing third-party resources, or modifying credentials.

When approval is ambiguous, produce a local plan or draft artifact instead of taking the external action. Preserve user config and private state unless the user specifically asks for a scoped change.

## Multi-Agent Support

Codex supports multi-agent workflows behind the `features.multi_agent` flag.

- Enable it in `.codex/config.toml` with `[features] multi_agent = true`
- Define project-local roles under `[agents.<name>]`
- Point each role at a TOML layer under `.codex/agents/`
- Use `/agent` inside Codex CLI to inspect and steer child agents

### Available Agents (15)

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

## Key Differences from Claude Code

| Feature | Claude Code | Codex CLI |
|---------|------------|-----------|
| Hooks | 8+ event types | Not yet supported |
| Context file | CLAUDE.md + AGENTS.md | AGENTS.md only |
| Skills | Skills loaded via plugin | `.agents/skills/` directory |
| Commands | `/slash` commands | Instruction-based |
| Agents | Subagent Task tool | Multi-agent via `/agent` and `[agents.<name>]` roles |
| Security | Hook-based enforcement | Instruction + sandbox |
| MCP | Full support | Supported via `config.toml` and `codex mcp add` |

## Security Without Hooks

Since Codex lacks hooks, security enforcement is instruction-based:
1. Always validate inputs at system boundaries
2. Never hardcode secrets — use environment variables
3. Run `npm audit` / `pip audit` before committing
4. Review `git diff` before every push
5. Use `sandbox_mode = "workspace-write"` in config
