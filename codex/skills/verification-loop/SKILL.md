---
name: verification-loop
description: Comprehensive verification system — build, typecheck, lint, test, security scan, diff review. Use after completing features, before PRs, or after refactoring.
---

# Verification Loop

Run all 6 phases in order. STOP on first failure.

## Phase 1: Build

```bash
pnpm build
```

If build fails → STOP and fix before continuing.

## Phase 2: Type Check

```bash
npx tsc --noEmit
```

Report all errors. Fix critical ones first.

## Phase 3: Lint

```bash
pnpm lint
```

Auto-fix what's possible, manually fix the rest.

## Phase 4: Test Suite

```bash
pnpm test -- --coverage
```

Target: 80% minimum coverage.
Report: total tests, passed, failed, coverage %.

## Phase 5: Security Scan

Search for leaked secrets:
```bash
grep -rn "sk-\|api_key\|password\|secret" --include="*.ts" --include="*.tsx" src/
```

Search for debug statements:
```bash
grep -rn "console\.log\|debugger" --include="*.ts" --include="*.tsx" src/
```

## Phase 6: Diff Review

```bash
git diff
```

Review each changed file for:
- Unintended changes
- Missing error handling
- Edge cases not covered
- Security issues

## Output Format

```
## VERIFICATION REPORT

| Phase | Status | Details |
|-------|--------|---------|
| Build | ✅/❌ | ... |
| Type Check | ✅/❌ | ... |
| Lint | ✅/❌ | ... |
| Tests | ✅/❌ | X passed, Y failed, Z% coverage |
| Security | ✅/❌ | ... |
| Diff Review | ✅/❌ | ... |

## READY / NOT READY for PR

### Issues to fix:
1. ...
```

## Continuous Mode

Run every 15 minutes or after major changes during long sessions.
Complements PostToolUse hooks with deeper verification.
