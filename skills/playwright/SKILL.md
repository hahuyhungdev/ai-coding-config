---
name: playwright
description: "Unified skill for Playwright E2E testing against real servers, automated visual/accessibility QA audits, Page Object Models, and terminal-driven browser automation."
---

# Playwright E2E & Browser QA

Consolidated guidelines for conducting real-server E2E browser testing, visual checks, accessibility audits, and interactive CLI browser automation using Playwright.

---

## ⚡ The Live-Server Testing Lifecycle

When verifying frontend applications, always prefer running E2E tests against a **live local server** rather than isolated mock components. Follow this lifecycle:

```
1. Boot Server ──→ 2. Port Check ──→ 3. Playwright E2E ──→ 4. Capture Logs/Screenshots ──→ 5. Shutdown Server
```

### Phase 1: Boot & Port Check
Always start the web server in the background and verify it is listening before launching browser tests:
```bash
# Start server in background (e.g. Vite or custom Python server)
npm run dev & 
# OR
python3 server.py --port 8000 &

# Wait for the port to accept connections
timeout 10 bash -c 'until echo > /dev/tcp/127.0.0.1/8000; do sleep 0.5; done'
```

### Phase 2: Spec Execution with Observability
Pipe page console logs and capture network errors during runs to ensure full debugging visibility:
```javascript
// In your Playwright script/spec
page.on('console', msg => {
  console.log(`[PAGE CONSOLE] ${msg.type().toUpperCase()}: ${msg.text()}`);
});
page.on('pageerror', err => {
  console.error(`[PAGE UNCAUGHT ERROR]: ${err.message}`);
});
```

### Phase 3: Artifact Collection & Cleanup
If a test fails, save a screenshot immediately and terminate the background server:
```javascript
// Capture failure artifact
await page.screenshot({ path: 'scratch/e2e-failure.png', fullPage: true });
```
```bash
# Kill background processes listening on the target port
kill $(lsof -t -i:8000) 2>/dev/null || true
```

---

## 📦 Page Object Model (POM) Design

Maintain highly readable, stable E2E tests by abstracting pages into Page Objects:

```typescript
import { Page, Locator } from '@playwright/test';

export class DashboardPage {
  readonly page: Page;
  readonly sidebar: Locator;
  readonly applyButton: Locator;
  readonly stagedChanges: Locator;

  constructor(page: Page) {
    this.page = page;
    this.sidebar = page.locator('aside');
    this.applyButton = page.locator('button:has-text("Apply Changes")');
    this.stagedChanges = page.locator('section:has-text("Staged Changes")');
  }

  async goto() {
    await this.page.goto('http://127.0.0.1:8000');
    await this.page.waitForLoadState('networkidle');
  }

  async applyStagedChanges() {
    await this.applyButton.click();
    await this.page.locator('button:has-text("Standard Apply")').click();
  }
}
```

---

## 🔍 Browser QA Checklists

Integrate these verification passes into your E2E flows to ensure production readiness:

### 1. Smoke & Network Pass
* Check for console `ERROR` and `WARN` logs.
* Verify no `4xx` or `5xx` status codes in network requests.
* Check that loading states/spinners clear within 2.5 seconds (LCP).

### 2. Responsive Visual Pass
* Test pages at three standard viewports:
  * **Desktop**: 1440 × 900
  * **Tablet**: 768 × 1024
  * **Mobile**: 375 × 667
* Flag overlapping text, broken flex/grid wraps, and horizontal page scrolling.

### 3. Accessibility (A11y) Pass
* Ensure key images have `alt` attributes.
* Verify form fields have associated `<label>` tags or `aria-label` properties.
* Verify keyboard focus works sequentially using Tab key navigation.

---

## 🖥️ Terminal-Driven Browser Automation

For interactive CLI-first exploration or quick debugging from the shell, use the bundled wrapper script `playwright_cli.sh`.

### Skill path (set once)
```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export PWCLI="$CODEX_HOME/skills/playwright/scripts/playwright_cli.sh"
```

### Quick Commands
```bash
# Open headed browser session
"$PWCLI" open http://127.0.0.1:8000 --headed

# Capture snapshot of elements to get reference IDs (e.g. e1, e2)
"$PWCLI" snapshot

# Click element and type
"$PWCLI" click e4
"$PWCLI" type "mysql-connector"
"$PWCLI" press Enter

# Capture screenshot of active state
"$PWCLI" screenshot
```

---

## 📊 E2E Test Report Template

Upon completion of E2E verification, generate a report structured as follows:

```markdown
# Playwright E2E QA Report

**Date:** YYYY-MM-DD HH:MM  
**Environment:** http://127.0.0.1:8000  
**Status:** ✅ PASSING / ❌ FAILING

## Summary
* **Specs Run**: X total
* **Console Errors**: 0 critical (Y warnings ignored)
* **Network Status**: All 200/304, zero failures

## Verified User Journeys
* [✓] **Tab Navigation**: All tabs load correct layout.
* [✓] **State Persistence**: Adding/discarding custom servers stages changes.
* [✓] **Install Stream**: Staged changes successfully run installer and stream stdout.

## Failure Logs & Artifacts (if applicable)
* **Failure**: `tests/dashboard.spec.ts:42` - element button not found
* **Screenshot**: `scratch/e2e-failure.png`
* **Log Output**: `[PAGE UNCAUGHT ERROR]: TypeError: Cannot read property 'map' of undefined`
```
