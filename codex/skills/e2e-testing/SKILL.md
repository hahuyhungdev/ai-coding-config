---
name: e2e-testing
description: Playwright E2E testing patterns — Page Object Model, configuration, CI/CD integration, artifact management, flaky test strategies. Use when writing E2E tests or debugging test failures.
---

# E2E Testing Patterns

## File Organization

```
tests/
├── e2e/
│   ├── auth/login.spec.ts
│   ├── features/search.spec.ts
│   └── api/endpoints.spec.ts
├── fixtures/auth.ts
└── playwright.config.ts
```

## Page Object Model

```typescript
export class ItemsPage {
  readonly page: Page
  readonly searchInput: Locator
  readonly itemCards: Locator

  constructor(page: Page) {
    this.page = page
    this.searchInput = page.locator('[data-testid="search-input"]')
    this.itemCards = page.locator('[data-testid="item-card"]')
  }

  async goto() { await this.page.goto('/items'); await this.page.waitForLoadState('networkidle') }
  async search(query: string) { await this.searchInput.fill(query); await this.page.waitForLoadState('networkidle') }
}
```

## Playwright Config

```typescript
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
})
```

## Flaky Test Fixes

### Race conditions
```typescript
// ❌ Bad
await page.click('[data-testid="button"]')
// ✅ Good
await page.locator('[data-testid="button"]').click()
```

### Network timing
```typescript
// ❌ Bad
await page.waitForTimeout(5000)
// ✅ Good
await page.waitForResponse(resp => resp.url().includes('/api/data'))
```

### Quarantine
```typescript
test('flaky test', async ({ page }) => {
  test.fixme(true, 'Flaky - Issue #123')
})
```

## CI/CD

```yaml
- run: npx playwright install --with-deps
- run: npx playwright test
- uses: actions/upload-artifact@v4
  if: always()
  with:
    name: playwright-report
    path: playwright-report/
```

## Artifacts

```typescript
await page.screenshot({ path: 'artifacts/after-login.png' })
// In config: video: 'retain-on-failure'
```
