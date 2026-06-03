---
name: eval-harness
description: Eval-driven development framework — define expected behavior before implementation, run evals continuously, track regressions. Use for EDD setup, pass/fail criteria, agent reliability measurement.
---

# Eval Harness

Core: evals are the "unit tests of AI development." Define expected behavior before implementation.

## When to Use

- Setting up eval-driven development
- Defining pass/fail criteria for AI outputs
- Measuring agent reliability (pass@k)
- Creating regression suites
- Benchmarking across model versions

## Eval Types

| Type | Purpose | Approach |
|------|---------|----------|
| Capability | Test if agent can accomplish tasks | Structured checklists |
| Regression | Ensure existing functionality isn't broken | Compare against baseline |

## Grader Approaches

1. **Code-Based** — deterministic (grep, test runners, build commands)
2. **Model-Based** — Claude evaluates on 1-5 rubric
3. **Human** — flags for manual review (LOW/MEDIUM/HIGH risk)

## Key Metrics

- **pass@k**: At least 1 success in k attempts. Target: pass@3 > 90%
- **pass^k**: All k trials succeed. Higher reliability bar for critical paths.

## 4-Phase Workflow

### 1. Define
Write eval definitions before any code:
```yaml
name: api-endpoint-creation
description: Agent should create a working REST endpoint
criteria:
  - Creates route file with correct HTTP method handler
  - Includes input validation (Zod)
  - Returns proper status codes
  - Handles errors gracefully
```

### 2. Implement
Write code to pass the evals.

### 3. Evaluate
Run evals frequently during development:
```bash
# Run specific eval
eval check api-endpoint-creation

# Run all evals
eval report
```

### 4. Report
Summarize capability + regression results with metrics.

## Best Practices

- Define evals BEFORE coding
- Run evals frequently
- Prefer code-based graders (deterministic)
- Use human review for security
- Keep evals fast (<30s each)
- Version evals alongside code as first-class artifacts
