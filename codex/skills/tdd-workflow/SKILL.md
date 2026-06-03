---
name: tdd-workflow
description: Test-Driven Development workflow — write tests first, implement to pass, refactor. Use for new features, bug fixes, refactoring, API endpoints, new components.
---

# TDD Workflow

Core principle: ALWAYS write tests first, then implement code to make tests pass.

## Coverage Goals

- Minimum 80% coverage across unit, integration, and E2E tests
- Cover edge cases, error scenarios, and boundary conditions

## Test Types

| Type | Covers | Tools |
|------|--------|-------|
| Unit | Individual functions, component logic, pure functions | Jest/Vitest |
| Integration | API endpoints, database ops, service interactions | Jest + test DB |
| E2E | Critical user flows, complete workflows, UI interactions | Playwright |

## 7-Step Workflow

### 1. Write User Journeys
```
As a [role], I want to [action], so that [benefit]
```

### 2. Generate Test Cases
Write comprehensive test cases for each journey.

### 3. Run Tests (Expect FAIL)
```bash
pnpm test
```
All tests should fail — implementation doesn't exist yet.

### 4. Implement Minimal Code
Write just enough code to make tests pass. Don't over-engineer.

### 5. Run Tests (Expect PASS)
```bash
pnpm test
```
All tests should pass now.

### 6. Refactor
Clean up code while keeping tests green.

### 7. Verify Coverage
```bash
pnpm test -- --coverage
```
Ensure 80%+ threshold is met.

## Code Patterns

### Unit Test (Vitest)
```typescript
import { describe, it, expect } from 'vitest'

describe('calculateSimilarity', () => {
  it('returns 0 for orthogonal vectors', () => {
    expect(calculateSimilarity([1,0,0], [0,1,0])).toBe(0)
  })

  it('returns 1 for identical vectors', () => {
    expect(calculateSimilarity([1,0,0], [1,0,0])).toBe(1)
  })
})
```

### API Integration Test
```typescript
import { POST } from './route'
import { NextRequest } from 'next/server'

it('returns 400 for invalid input', async () => {
  const req = new NextRequest('http://localhost/api/test', {
    method: 'POST',
    body: JSON.stringify({})
  })
  const res = await POST(req)
  expect(res.status).toBe(400)
})
```

### E2E Test (Playwright)
```typescript
import { test, expect } from '@playwright/test'

test('user can complete flow', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Start' }).click()
  await expect(page.getByText('Complete')).toBeVisible()
})
```

## Anti-Patterns

- ❌ Testing implementation details instead of behavior
- ❌ Brittle CSS selectors instead of semantic queries
- ❌ Tests that depend on each other
- ❌ Skipping error path tests
- ❌ Writing tests after implementation

## File Organization

- Co-locate tests with source: `Button.tsx` → `Button.test.tsx`
- E2E specs in dedicated `e2e/` directory

## Success Metrics

- 80%+ coverage
- All tests passing
- No skipped tests
- Unit tests < 50ms each
- E2E covers critical flows
