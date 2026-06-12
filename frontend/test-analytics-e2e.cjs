const { chromium } = require('playwright');
const path = require('path');

(async () => {
  console.log("Starting E2E test for Analytics Tab...");
  let browser;
  try {
    browser = await chromium.launch({
      channel: 'msedge',
      headless: true
    });
    
    const context = await browser.newContext({
      viewport: { width: 1280, height: 800 }
    });
    const page = await context.newPage();
    
    page.on('console', msg => {
      console.log(`[PAGE CONSOLE] ${msg.type().toUpperCase()}: ${msg.text()}`);
    });
    
    console.log("Navigating to http://127.0.0.1:8555...");
    await page.goto('http://127.0.0.1:8555', { waitUntil: 'networkidle' });
    
    // 1. Verify Page Title
    const title = await page.title();
    console.log(`Page title: ${title}`);
    if (!title.includes("AI Coding Config Dashboard")) {
      throw new Error(`Unexpected page title: ${title}`);
    }
    
    // 2. Click Observability Tab
    console.log("Clicking on 'Observability' tab...");
    await page.click('header >> text="Observability"');
    await page.waitForTimeout(2000); // Wait for API call & rendering
    
    // 3. Verify content rendered on Observability Dashboard
    console.log("Verifying content rendered on Observability Dashboard...");
    let content = await page.textContent('body');
    
    if (!content.includes("Observability & Token Analytics")) {
      throw new Error("Observability heading not found on the page.");
    }
    if (!content.includes("Cost Leverage: Pro vs. Flash")) {
      throw new Error("Cost savings gauge section not found on the page.");
    }
    if (!content.includes("Session History Directory")) {
      throw new Error("Session history table section not found on the page.");
    }
    
    console.log("Observability Dashboard elements successfully verified.");
    
    // 4. Click on the first session in the history directory table
    console.log("Clicking first session row in the history directory table...");
    await page.click('table tbody tr:first-child');
    await page.waitForTimeout(2000); // Wait for transition and API load
    
    // 5. Verify conversation viewer loaded
    content = await page.textContent('body');
    if (!content.includes("Input") || !content.includes("Output") || !content.includes("Cost")) {
      throw new Error("Failed to transition to conversation detail logs viewer.");
    }
    console.log("Successfully transitioned to detailed conversation viewer.");
    
    // 6. Capture screenshot
    const screenshotPath = path.join(__dirname, '..', 'observability-merged-view-check.png');
    console.log(`Capturing screenshot to ${screenshotPath}...`);
    await page.screenshot({ path: screenshotPath });
    console.log("Screenshot saved.");
    
    console.log("Observability Merged E2E test completed successfully!");
    process.exit(0);
  } catch (error) {
    console.error("Analytics E2E test failed with error:", error);
    process.exit(1);
  } finally {
    if (browser) {
      await browser.close();
    }
  }
})();
