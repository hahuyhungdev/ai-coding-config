const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const ARTIFACTS_DIR = process.env.ARTIFACTS_DIR || path.join(__dirname, '..', 'scratch', 'visual_audit');
if (!fs.existsSync(ARTIFACTS_DIR)) {
  fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });
}

const PORT = process.env.PORT || '8000';

(async () => {
  console.log("🚀 Starting Playwright UI/UX & A11y Audit...");
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const consoleLogs = [];
  const pageErrors = [];

  // Register listeners
  page.on('console', msg => {
    const text = msg.text();
    consoleLogs.push({ type: msg.type(), text });
    if (msg.type() === 'error') {
      console.error(`[PAGE CONSOLE ERROR] ${text}`);
    }
  });

  page.on('pageerror', err => {
    pageErrors.push(err.message);
    console.error(`[PAGE UNCAUGHT ERROR] ${err.message}`);
  });

  try {
    // 1. Initial Load & Viewport Setup
    console.log(`Navigating to http://127.0.0.1:${PORT}...`);
    await page.goto(`http://127.0.0.1:${PORT}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // 2. Responsive Visual Checks (Desktop, Tablet, Mobile)
    console.log("\n--- Responsive Visual Checks ---");
    const viewports = [
      { name: 'desktop', width: 1440, height: 900 },
      { name: 'tablet', width: 768, height: 1024 },
      { name: 'mobile', width: 375, height: 667 }
    ];

    for (const vp of viewports) {
      console.log(`Setting viewport to ${vp.name} (${vp.width}x${vp.height})`);
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.waitForTimeout(500);
      
      const screenshotPath = path.join(ARTIFACTS_DIR, `dashboard_${vp.name}.png`);
      await page.screenshot({ path: screenshotPath, fullPage: false });
      console.log(`  -> Saved screenshot: ${screenshotPath}`);
    }

    // Set back to desktop for the rest of the tests
    await page.setViewportSize({ width: 1440, height: 900 });

    // 3. Accessibility & Structure Audit
    console.log("\n--- Accessibility & Semantic HTML Audit ---");
    const a11yAudit = await page.evaluate(() => {
      const issues = [];

      // A. Form elements missing associated labels or aria-labels
      const formControls = Array.from(document.querySelectorAll('input, select, textarea'));
      formControls.forEach(ctrl => {
        if (ctrl.type === 'hidden' || ctrl.type === 'checkbox') return;
        
        let hasLabel = false;
        // Check if it has an id and there's a label pointing to it
        if (ctrl.id) {
          const label = document.querySelector(`label[for="${ctrl.id}"]`);
          if (label && label.textContent.trim()) hasLabel = true;
        }
        // Check if nested in a label
        if (ctrl.closest('label')) hasLabel = true;
        // Check for aria-label or aria-labelledby
        if (ctrl.getAttribute('aria-label') || ctrl.getAttribute('aria-labelledby')) hasLabel = true;
        // Check for placeholder as backup (less ideal for screenreaders)
        const hasPlaceholder = !!ctrl.getAttribute('placeholder');

        if (!hasLabel) {
          issues.push({
            type: 'Form Control Missing Label',
            element: `${ctrl.tagName.toLowerCase()}${ctrl.id ? '#' + ctrl.id : ''}${ctrl.name ? '[name=' + ctrl.name + ']' : ''}`,
            suggestion: 'Add an id and a matching <label for="..."> tag, or add an aria-label attribute.',
            critical: !hasPlaceholder
          });
        }
      });

      // B. Images missing alt descriptions
      const images = Array.from(document.querySelectorAll('img'));
      images.forEach(img => {
        const alt = img.getAttribute('alt');
        if (alt === null) {
          issues.push({
            type: 'Image Missing Alt Text',
            element: img.outerHTML.substring(0, 100),
            suggestion: 'Add an alt="..." description (or empty alt="" if purely decorative).',
            critical: true
          });
        }
      });

      // C. Navigation landmarks
      const navCount = document.querySelectorAll('nav').length;
      if (navCount === 0) {
        issues.push({
          type: 'No Navigation Landmark',
          element: 'header/menu',
          suggestion: 'Wrap tab navigation list inside a <nav> tag for accessibility.',
          critical: false
        });
      }

      // D. Heading structure
      const h1Count = document.querySelectorAll('h1').length;
      if (h1Count > 1) {
        issues.push({
          type: 'Multiple H1 Headings',
          element: `Found ${h1Count} <h1> elements`,
          suggestion: 'Ensure there is only a single <h1> heading per page for SEO and screenreaders.',
          critical: false
        });
      }

      return {
        issues,
        totalControls: formControls.length,
        totalImages: images.length
      };
    });

    console.log(`Audited ${a11yAudit.totalControls} form controls and ${a11yAudit.totalImages} images.`);
    if (a11yAudit.issues.length === 0) {
      console.log("✅ Accessibility Audit: PASS (No critical issues found!)");
    } else {
      console.log(`⚠️ Accessibility Audit: Found ${a11yAudit.issues.length} potential improvements:`);
      a11yAudit.issues.forEach((issue, i) => {
        console.log(`  [${i + 1}] [${issue.critical ? 'CRITICAL' : 'SUGGESTION'}] ${issue.type} on <${issue.element}>`);
        console.log(`      Advice: ${issue.suggestion}`);
      });
    }

    // 4. Tab Navigation and Quality Check
    console.log("\n--- Tab Quality & Visual Verification ---");
    const tabs = ['Dashboard', 'MCP', 'Claude', 'Codex', 'Gemini', 'Agents', 'Code Graph', 'Simulator'];
    for (const tab of tabs) {
      console.log(`Checking Tab: "${tab}"`);
      await page.click(`header >> text="${tab}"`);
      await page.waitForTimeout(800);
      
      const safeTabName = tab.toLowerCase().replace(' ', '_');
      const tabScreenshotPath = path.join(ARTIFACTS_DIR, `tab_${safeTabName}.png`);
      await page.screenshot({ path: tabScreenshotPath });
      console.log(`  -> Saved tab screenshot: ${tabScreenshotPath}`);
    }

    // 5. Audit Summary Report Generation
    console.log("\n--- Audit Summary ---");
    console.log(`Console Warning/Error Count: ${consoleLogs.filter(l => l.type === 'warning' || l.type === 'error').length}`);
    console.log(`Page Uncaught Errors: ${pageErrors.length}`);

    // Write audit findings to JSON for the builder to consume
    const reportData = {
      timestamp: new Date().toISOString(),
      url: page.url(),
      consoleLogs,
      pageErrors,
      a11yAudit
    };

    fs.writeFileSync(
      path.join(ARTIFACTS_DIR, 'playwright_ui_audit.json'),
      JSON.stringify(reportData, null, 2)
    );
    console.log(`\n✅ Audit completed. Full JSON report saved to ${path.join(ARTIFACTS_DIR, 'playwright_ui_audit.json')}`);

  } catch (err) {
    console.error("❌ Audit script failed with exception:", err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
