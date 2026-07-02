---
name: playwright
description: Guides the usage of the Playwright MCP server to control real browsers, capture screenshots, audit layouts, and perform automated interactive actions.
---

# Playwright Browser Automation & MCP Auditing

This skill guides the control of real browsers directly from the agent session using the `playwright` MCP server, enabling live audits, visual checks, and interactive task execution.

## 1. Playwright MCP Tool Suite

Use the following `playwright` MCP tools via `call_mcp_tool` to interact with the browser:

- **`browser_navigate`:** Navigates to a target URL (e.g., local Vite dev server `http://localhost:5173`).
- **`browser_resize`:** Resizes the browser viewport (use standard widths: Desktop `1440x900` or Mobile `375x667`).
- **`browser_take_screenshot`:** Captures a PNG/JPEG screenshot of the current page. Save visual audits to `.frontend-scan-screens/` or temporary checks to `scratch/`.
- **`browser_snapshot`:** Extracts a structured tree of the DOM, displaying interactive elements and their corresponding IDs or CSS selectors.
- **`browser_click`:** Simulates clicking a specific element by selector or reference ID.
- **`browser_type` / `browser_fill_form`:** Types text into input fields or fills out complex form schemas.
- **`browser_press_key`:** Simulates keyboard key presses (e.g., `Enter`, `Tab`, `ArrowDown`).
- **`browser_evaluate`:** Evaluates a custom JavaScript snippet in the page context to extract dynamic states.
- **`browser_console_messages`:** Fetches recent console.log, warnings, or errors output by the page.
- **`browser_network_requests`:** Audits recent HTTP requests to check for `4xx`/`5xx` api response failures.

---

## 2. Interactive Navigation & Action Flow

Follow these sequential steps to perform interactive actions on web applications:

```
1. Navigate ──→ 2. Snapshot ──→ 3. Interact (Click/Fill) ──→ 4. Verify (Screenshot/Console)
```

### Step 1: Navigate to target
Always verify the local server is running, then navigate to it:
```javascript
// Navigates the browser instance to local port
await browser_navigate({ url: "http://localhost:5173" })
```

### Step 2: Take a snapshot to locate selectors
Do not guess element selectors. Run a snapshot to get clean DOM references:
```javascript
// Fetch DOM structure
const snapshot = await browser_snapshot()
```
Identify the target button or input field (e.g., `#add-mcp-btn` or a button containing text "Save changes").

### Step 3: Perform interactions
Simulate user actions sequentially. Wait for the page or network to settle between interactions:
```javascript
// Fill connection details
await browser_fill_form({ target: "input[name='mcpName']", value: "filesystem" })
// Click save button
await browser_click({ target: "button:has-text('Save')" })
```

### Step 4: Verify console & logs
Ensure no uncaught JS exceptions occurred during the action:
```javascript
const logs = await browser_console_messages()
// Flag any log entries containing "error" or "exception"
```

---

## 3. Visual & Responsive Design Auditing

When conducting design systems audits, test layout responsiveness and dark theme completeness across viewports:

1. **Desktop Audit (1440x900):**
   - Resize: `browser_resize({ width: 1440, height: 900 })`
   - Capture: `browser_take_screenshot({ filename: ".frontend-scan-screens/desktop_view.png" })`
   - Check: Grid alignments, text spacing, header positioning.

2. **Mobile Audit (375x667):**
   - Resize: `browser_resize({ width: 375, height: 667 })`
   - Capture: `browser_take_screenshot({ filename: ".frontend-scan-screens/mobile_view.png" })`
   - Check: Sidebar overlay displays, hamburger menus, no horizontal scrolling.

3. **Accessibility (A11y) Focus Ring Audit:**
   - Run tab commands: `browser_press_key({ key: "Tab" })`
   - Take a screenshot: `browser_take_screenshot({ filename: "scratch/focus_ring_check.png" })`
   - Verify: Clear `:focus-visible` outlines are visible on navigation buttons.
