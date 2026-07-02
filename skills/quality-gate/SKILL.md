---
name: quality-gate
description: Enforces test-driven development (TDD) pre-implementation and runs the comprehensive build, typecheck, lint, test, and security verification check post-implementation.
---

# Code Quality Gate & Verification Workflow

This skill ensures all code changes are structurally validated before implementation using Test-Driven Development (TDD) and verified post-implementation through a strict Quality Gate checklist.

## 1. Quality Gate Entry: Test-Driven Development (TDD)

Use this flow when writing new features, fixing bugs, or refactoring existing code.

### Step 1: Define the Test Case & Expected Fail (RED)
- Always write the test cases **before** writing/modifying business logic.
- Run the test suite and verify that the new test fails.
- The failure must be due to the missing implementation/bug, not configuration or syntax errors.
- **Git Checkpoint:** Create a checkpoint commit named: `test: add reproducer for <feature or bug>`.

### Step 2: Implement Minimal Code
- Write the minimum amount of production code needed to satisfy the test case.
- Avoid premature optimizations or speculative functionality not requested.

### Step 3: Verify the Test Passes (GREEN)
- Run the test suite again and confirm the test now passes.
- **Git Checkpoint:** Create a checkpoint commit named: `fix: <feature or bug>` or `feat: <feature>`.

### Step 4: Refactor Under Green Safety
- Clean up duplication, improve variable names, and optimize logic while keeping tests passing.
- **Git Checkpoint:** Create a checkpoint commit named: `refactor: clean up <feature or bug>`.

---

## 2. Quality Gate Exit: Verification Loop

Before creating a Pull Request or declaring a task complete, you must run the following check loop:

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
- Ensure the project maintains a **minimum 80% coverage** threshold.
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
