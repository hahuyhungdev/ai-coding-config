---
name: karpathy-guidelines
description: Use for non-trivial code review, risky refactors, or implementation planning where LLM coding mistakes are likely: overcomplication, speculative abstractions, mutation bugs, broad unrelated edits, or weak verification. Do not use for simple one-line edits or routine variable renames.
---

# Code Quality & Simplicity Standards (Karpathy Guidelines)

Conventions and behavioral guidelines to reduce common LLM coding pitfalls, prioritize simplicity, enforce clean coding standards, and ensure surgical code modifications.

---

## 1. Simplicity First (KISS, DRY, YAGNI)

- **Write the minimum code that solves the problem.** Nothing speculative.
- Do not build features or configurations beyond what was explicitly asked.
- Avoid abstractions for single-use code.
- If a function is over 50 lines or code is overcomplicated, stop and rewrite it.
- **Surgical Changes:** Touch only what you must. Match existing style. Do not refactor adjacent code that is not broken. Clean up only unused imports/variables created by YOUR changes.

---

## 2. Immutability & Variable/Function Naming

### Immutability Default (CRITICAL)
- **Never mutate state or arrays directly.** Always use copy-and-update spread patterns:
```typescript
// GOOD: Pure updates
const updatedUser = { ...user, name: 'New Name' };
const updatedArray = [...items, newItem];

// BAD: Direct mutations
user.name = 'New Name';
items.push(newItem);
```

### Descriptive Naming Patterns
- **Variables:** Use descriptive nouns or booleans showing state. Avoid single letters or generic flags:
  - `const marketSearchQuery = 'election'` (Good) vs `const q = 'election'` (Bad)
  - `const isUserAuthenticated = true` (Good) vs `const flag = true` (Bad)
- **Functions:** Use a clear **verb-noun** pattern:
  - `async function fetchMarketData(id: string)` (Good) vs `async function market(id: string)` (Bad)

---

## 3. Defensive Programming & Error Handling

- Always handle async errors using try-catch blocks.
- Never let exceptions fail silently or leak raw database stack traces to the output.
- **Early Returns:** Avoid deeply nested `if` statements (limit nesting to 3 levels). Use guard clauses and return early:
```typescript
// GOOD: Early returns
if (!user) return;
if (!user.isAdmin) return;
// execute admin action...

// BAD: Nesting hell
if (user) {
  if (user.isAdmin) {
    // execute admin action...
  }
}
```

---

## 4. Documentation & Magic Numbers

### Explain WHY, not WHAT
- Comments should document developer intent, hacks, or non-obvious workarounds, not re-state what the code does.
```typescript
// GOOD: Explains non-obvious workaround
// Using direct mutation here for high-frequency chart rendering performance
points.push(newPoint);

// BAD: Stating the obvious
// Push newPoint to points array
points.push(newPoint);
```

### Avoid Magic Numbers
- Declare constants with descriptive uppercase names instead of hardcoding raw values:
```typescript
const MAX_CONNECTION_RETRIES = 3;
const API_DEBOUNCE_DELAY_MS = 500;

if (retryCount > MAX_CONNECTION_RETRIES) { ... }
```

---

## 5. Goal-Driven Execution

- **Define success criteria before writing code.**
- "Fix the bug" ➔ write a test that reproduces the bug, then make it pass.
- "Refactor X" ➔ verify compilation and tests pass before and after changes.
- Transform tasks into verifiable steps:
  ```
  1. [Step] ➔ verify: [check]
  2. [Step] ➔ verify: [check]
  ```
