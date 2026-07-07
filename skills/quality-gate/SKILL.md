---
name: quality-gate
description: Use for behavior changes, bug fixes, risky refactors, test-driven development, red-green-refactor, vertical-slice testing, public-interface behavior tests, or explicit verification requests where fresh evidence is required before claiming success. Do not use for routine renames, formatting-only edits, documentation-only edits, or simple config reads.
---

# Code Quality Gate & Verification Workflow

This skill ensures behavioral and risky code changes are structurally validated before implementation using Test-Driven Development (TDD) and verified post-implementation through a strict Quality Gate checklist.

## When to Use

Use this skill for behavior changes, bug fixes, risky refactors, public-interface tests, explicit verification requests, or any work where fresh test evidence is required before claiming success. For documentation-only or formatting-only edits, run the smallest relevant validation instead.

## 1. Quality Gate Entry: Test-Driven Development (TDD)

Use this flow when writing new features, fixing bugs, or refactoring behavior-sensitive code. For routine renames, formatting-only edits, documentation-only edits, or simple config reads, run only the smallest relevant validation instead.

### Testing Principle
- Test behavior through public interfaces, not private implementation details.
- Prefer integration-style tests that exercise real code paths at the seam users or callers rely on.
- A good test survives internal refactors. If a harmless rename breaks the test, the test is coupled to implementation.
- Mock only external systems or slow/unreliable dependencies. Do not mock internal collaborators just to make testing easy.

### Anti-Pattern: Horizontal Slices
Do not write all tests first and then all implementation. That locks in imagined behavior before the first implementation teaches you anything.

Use vertical slices:

```text
RED -> GREEN for behavior 1
RED -> GREEN for behavior 2
RED -> GREEN for behavior 3
```

### Step 1: Define One Behavior & Expected Fail (RED)
- Identify the public interface or user path being tested.
- Write one focused test for one observable behavior.
- Run it and verify that it fails for the missing behavior or reproduced bug.
- The failure must not be caused by syntax, setup, or fixture errors.

### Step 2: Implement Minimal Code
- Write the minimum amount of production code needed to satisfy the test case.
- Avoid premature optimizations or speculative functionality not requested.

### Step 3: Verify the Test Passes (GREEN)
- Run the test suite again and confirm the test now passes.
- Create commits only when the user asks for commits or the repo workflow explicitly requires them.

### Step 4: Refactor Under Green Safety
- Clean up duplication, improve variable names, and optimize logic while keeping tests passing.
- Run the relevant tests after each meaningful refactor step.
- Never refactor while RED.

### Per-Cycle Checklist
```text
[ ] Test describes behavior, not implementation
[ ] Test uses the public interface or user path
[ ] Test would survive internal refactor
[ ] Code is minimal for this test
[ ] No speculative behavior added
```

---

## 2. Quality Gate Exit: Verification Loop

Before creating a Pull Request or declaring a task complete, run the checks that prove the actual claim. Do not claim success from stale or partial evidence.

If a command is unavailable or inappropriate for the repo, report that explicitly and run the nearest local equivalent.

### Phase 1: Build Verification
```bash
# Verify the project compiles cleanly
npm run build
```

### Phase 2: Type Check
```bash
# TypeScript projects
npx tsc --noEmit

# Python projects
pyright .
```

### Phase 3: Lint Check
```bash
# JavaScript/TypeScript
npm run lint

# Python
ruff check .
```

### Phase 4: Test & Coverage Gate
- Verify that unit/integration/E2E test suites run successfully.
- Respect the project's configured coverage threshold. If no threshold exists, report coverage as evidence without inventing a hard gate.
```bash
npm run test -- --coverage
```

### Phase 5: Security & Log Cleanliness Audit
- Check that no API keys, secrets, or temporary debugging logs (`console.log`) are left in production files.
```bash
# Check for stray secrets or console logs
grep -rn "console.log" --include="*.ts" --include="*.tsx" src/
```

### Phase 6: Git Diff Review
```bash
git diff --stat
```
Verify that every modified line is necessary, clean, and traces directly back to the user request.

---

## 3. Verification Report Format

Upon completing the verification loop, generate a concise checklist inside the chat:

```
VERIFICATION REPORT
==================
Build:     [PASS/FAIL]
Types:     [PASS/FAIL] (X errors)
Lint:      [PASS/FAIL] (X warnings)
Tests:     [PASS/FAIL] (X/Y passed, Z% coverage)
Security:  [PASS/FAIL] (No secrets or stray console logs)
Diff:      [X files changed]

Overall:   [READY/NOT READY] for PR
```
