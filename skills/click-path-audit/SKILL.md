---
name: click-path-audit
description: Trace every interactive element (button/form/toggle) through its full handler call sequence to find bugs where individual functions work but cancel each other via shared state side effects. Use after major refactors touching Zustand/Context/Redux, or when users report a broken button that passes all unit tests.
metadata:
  origin: ECC (adapted)
---

# Click-Path Audit — Behavioural Flow Audit

Find bugs that static analysis and unit tests miss: **state interaction side effects**, race conditions between sequential calls, and handlers that silently undo each other.

## The Problem This Solves

Standard debugging checks:
- Does the function exist? (missing wiring)
- Does it crash? (runtime errors)
- Does it return the right type? (data flow)

**It does NOT check:**
- Does the final UI state match what the button label promises?
- Does function B silently undo what function A just did?
- Does shared state (Zustand/Redux/Context) have side effects that cancel the intended action?

**Real example:** A "New Email" button called `setComposeMode(true)` then `selectThread(null)`. Both worked individually. But `selectThread` had a side effect resetting `composeMode: false`. The button did nothing. 54 bugs were found by other debugging methods — this one was missed.

## When to Use

- Systematic debugging found no bugs but users still report broken interactive elements
- After any major refactor touching shared state stores
- Before shipping a feature that involves multiple state mutations in a single handler
- When a Playwright E2E test passes but the visual outcome is wrong

## How It Works

For EVERY interactive touchpoint in the target area:

```
1. IDENTIFY the handler (onClick, onSubmit, onChange, etc.)
2. TRACE every function call in the handler, IN ORDER
3. For EACH function call:
   a. What state does it READ?
   b. What state does it WRITE?
   c. Does it have SIDE EFFECTS on shared state?
   d. Does it reset/clear any state as a side effect?
4. CHECK: Does any later call UNDO a state change from an earlier call?
5. CHECK: Is the FINAL state what the user expects from the button label?
6. CHECK: Are there race conditions (async calls resolving in wrong order)?
```

## Execution Steps

### Step 1: Map State Stores

Before auditing any touchpoint, build a side-effect map of every state store action:

```
For each Zustand store / React context in scope:
  For each action/setter:
    - What fields does it set?
    - Does it RESET other fields as a side effect?
    - Document: actionName → {sets: [...], resets: [...]}
```

**Output format:**
```
STORE: emailStore
  setComposeMode(bool) → sets: {composeMode}
  selectThread(thread|null) → sets: {selectedThread, messages} RESETS: {composeMode: false}

DANGEROUS RESETS (actions that clear state they don't own):
  selectThread → resets composeMode (owned by setComposeMode)
```

### Step 2: Audit Each Touchpoint

For each button/toggle/form submit in the target area:

```
TOUCHPOINT: [Button label] in [Component:line]
  HANDLER: onClick → {
    call 1: functionA() → sets {X: true}
    call 2: functionB() → sets {Y: null} RESETS {X: false}  ← CONFLICT
  }
  EXPECTED: User sees [what the button label promises]
  ACTUAL: X is false because functionB reset it
  VERDICT: BUG — [description]
```

**Bug patterns to check:**

1. **Sequential Undo** — later call resets state from earlier call
2. **Async Race** — two async calls, loser overwrites winner's state
3. **Optimistic Update Cancelled** — optimistic state set, then error handler reverts more than intended
4. **Shared Reset** — a store action resets fields it doesn't own as a "cleanup" side effect

### Step 3: Report

Produce a summary:

```
## Click-Path Audit: [Component/Feature]

### State Store Map
[Side-effect table from Step 1]

### Touchpoint Results
[Table: Touchpoint | Verdict | Bug type | Recommended fix]

### Summary
- X touchpoints audited
- Y bugs found (Z critical, W minor)
- Top issue: [pattern]
```

## Scope Management

This audit can be time-intensive. Always **scope it explicitly**:

```
# Narrow scope example:
"Audit only the compose panel interaction: New Email, Reply, Discard buttons"

# Broad scope example (avoid unless necessary):
"Audit all interactive elements in the inbox view"
```

Start narrow, expand if initial findings show systemic issues.

## Integration with Existing Skills

- Run **after** `playwright` E2E tests pass but behavior is still wrong → click-path-audit finds the state logic gap
- Run **before** `tdd-workflow` on complex handlers → audit first reveals which state mutations need tests
- Run **after** major refactors that `verification-loop` flags as risky
