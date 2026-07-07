---
name: diagnosing-bugs
description: Use for hard bugs, regressions, flaky behavior, performance regressions, failing user flows, runtime exceptions, inconsistent behavior, or issues that are impossible to reproduce. Builds a tight red-capable feedback loop before hypothesizing or fixing.
---

# Diagnosing Bugs

Use this skill to avoid trial-and-error fixes. The first deliverable is a feedback loop that can prove the reported symptom.

## When to Use

Use this skill for hard bugs, regressions, flaky behavior, runtime exceptions, performance regressions, or user flows that fail without an obvious local cause. Do not use it for a straightforward compile error where the failing command already names the fix.

## 1. Build The Loop First

Before proposing causes or editing production code, create the smallest agent-runnable check that can catch the exact bug.

Prefer these loops, in order:

1. Failing test at the seam that reaches the bug.
2. `curl` or HTTP script against a running local server.
3. CLI command with fixture input and expected output.
4. Playwright or browser script that asserts DOM, console, network, or storage state.
5. Replay of captured request, payload, trace, or log.
6. Throwaway harness that calls the relevant module directly.
7. Seeded property or fuzz loop when the symptom is intermittent.
8. `git bisect run` command when the regression window is known.

The loop must be:

- **Red-capable:** it asserts the user's exact symptom, not just "does not crash".
- **Deterministic enough:** same result each run, or a raised reproduction rate for flaky bugs.
- **Fast:** seconds when possible.
- **Agent-runnable:** no hidden manual clicks unless captured in a documented human-in-the-loop script.

If no loop can be built, stop and report what artifact is missing: environment access, logs, HAR, trace, fixture, screen recording, or permission to instrument.

## 2. Reproduce And Minimize

Run the loop and confirm it fails for the same symptom the user reported.

Then shrink the scenario one variable at a time:

- remove inputs,
- narrow config,
- reduce data,
- cut steps,
- isolate callers.

Keep only pieces that are load-bearing for the failure.

## 3. Hypothesize After Evidence

List 3-5 ranked hypotheses only after the loop exists. Each hypothesis must be falsifiable:

```text
If <cause> is true, then <probe/change> should make <observable result>.
```

Test one variable at a time. Prefer debugger or REPL inspection when available; otherwise add targeted logs at decision boundaries. Tag temporary logs with a unique prefix such as `[DEBUG-a4f2]` so cleanup is mechanical.

For performance regressions, measure before changing code. Establish a baseline, then compare after each probe.

## 4. Fix With Regression Coverage

Turn the minimized repro into a failing regression test when there is a correct seam. A correct seam exercises the real bug pattern as it happens at the call site.

If no correct seam exists, record that as an architecture finding and keep the original feedback loop as the verification surface.

Fix only after the failing loop/test is understood. Then verify:

1. Regression test fails before the fix and passes after the fix, when applicable.
2. Original loop no longer reproduces the bug.
3. Related test/build/lint checks pass for the touched surface.
4. Temporary debug instrumentation and harness artifacts are removed or clearly marked.

## 5. Postmortem

Before declaring done, state:

- the confirmed root cause,
- the command that reproduced the bug,
- the command that proves the fix,
- whether a better seam or deeper module would have prevented the bug.
