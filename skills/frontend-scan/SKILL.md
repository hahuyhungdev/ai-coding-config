---
name: frontend-scan
description: Use this skill to perform a comprehensive audit and visual scan of the frontend interface before starting any UI task. It starts the local server, runs Playwright to capture screenshots (saving them to a gitignored folder), scores the UI, checks for AI slop, and saves the final markdown report.
---

# Frontend Scan — Comprehensive Visual & Technical UI Auditor

Use this skill at the beginning of any frontend task to audit the existing interface for style consistency, layout, responsiveness, and technical standards before writing any code.

## 1. Execution Workflow

To perform a complete scan, the Agent must execute these steps:

### Step 1: Start the Local Development Server
- Check if a local server is already running (e.g. check active ports).
- If not running, start the dev server (usually `npm run dev` or `npm run start`) inside the frontend workspace directory in the background as a task.
- Wait for the server to be ready and identify the local URL (typically `http://localhost:5173` or `http://localhost:3000`).

### Step 2: Open Playwright Browser MCP
- Start the Playwright Browser MCP server.
- Navigate to the identified local URL.

### Step 3: Capture Screenshots & Visual Evaluation
- Capture screenshots of key pages (e.g. Home/Landing, Dashboard, Settings) on both desktop (1440px width) and mobile (375px width) viewports.
- **Screenshot Storage:** Save all captured screenshots in the directory `./.frontend-scan-screens/` at the project root.
- **Gitignore Enforcement:** Ensure that `./.frontend-scan-screens/` is added to the project's `.gitignore` file to prevent committing image binaries to version control.
- Evaluate the visual layout, spacing rhythm, typography, contrast, responsiveness, and dark mode completeness.

### Step 4: AI Slop & Cliché Check
- Scan the rendered layout and codebase for generic AI-generated templates:
  - Default purple-to-blue gradients.
  - Gratuitous card glassmorphism.
  - Excessive decorative animations.
  - Stock layouts without custom branding or characterful font choices.

### Step 5: Generate & Save the Analysis Report
- Save the final audit notes as a markdown file at `./.frontend-scan-report.md` (or inside `docs/` if preferred).
- The report must include:
  1. Active server URL and tested ports.
  2. Scoring (0-10) across key dimensions (color consistency, responsive behavior, typography, accessibility contrast, polish).
  3. Screenshot list with absolute file links (e.g. `[Screenshot name](file:///path/to/project/.frontend-scan-screens/screenshot.png)`).
  4. Specific visual/code recommendations with file paths and line numbers.

---

## 2. Slash Commands & Triggers

To initiate the scan, the user can call:
```bash
/frontend-scan --url <local-url>
```
Or simply ask the agent:
- "Scan the frontend interface"
- "Audit the UI aesthetics on localhost"
- "Quét và đánh giá giao diện website"
- "frontend-scan"
