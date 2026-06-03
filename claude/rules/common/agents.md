# Agent Orchestration

## Available Agents

Located in `.claude/agents/`:

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| planner | Implementation planning | Complex features, refactoring |
| code-reviewer | Code review | After writing code |
| security-reviewer | Security analysis | Before commits, API changes |
| typescript-reviewer | TS/JS code review | TypeScript-specific issues |
| build-error-resolver | Fix build errors | When build fails |
| tdd-guide | Test-driven development | New features, bug fixes |
| database-reviewer | PostgreSQL/Drizzle review | Schema changes, queries |
| refactor-cleaner | Dead code cleanup | Code maintenance |

## Immediate Agent Usage (No User Prompt Needed)

1. Complex feature requests → **planner** agent
2. Code just written/modified → **code-reviewer** agent
3. Bug fix or new feature → **tdd-guide** agent
4. Build failure → **build-error-resolver** agent
5. API route changes → **security-reviewer** agent
6. Schema/query changes → **database-reviewer** agent

## Parallel Task Execution

ALWAYS use parallel agents for independent operations:

```
# GOOD: Parallel
Agent 1: Security analysis of auth module
Agent 2: Performance review of cache system
Agent 3: Type checking of utilities

# BAD: Sequential when unnecessary
First agent 1, then agent 2, then agent 3
```

## Multi-Perspective Analysis

For complex problems, use split role sub-agents:
- Factual reviewer
- Senior engineer
- Security expert
- Consistency reviewer
