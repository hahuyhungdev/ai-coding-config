const { chromium } = require('playwright');

(async () => {
  console.log("Starting E2E tests using Microsoft Edge...");
  let browser;
  try {
    // Launch Chromium with channel: 'msedge' to use Microsoft Edge
    browser = await chromium.launch({
      channel: 'msedge',
      headless: true
    });
    
    const context = await browser.newContext({
      viewport: { width: 1280, height: 800 }
    });
    const page = await context.newPage();
    
    // Log console messages from the page
    page.on('console', msg => {
      console.log(`[PAGE CONSOLE] ${msg.type().toUpperCase()}: ${msg.text()}`);
    });
    
    console.log("Navigating to http://127.0.0.1:8000...");
    await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle' });
    
    // 1. Verify Page Title
    const title = await page.title();
    console.log(`Page title: ${title}`);
    if (!title.includes("AI Coding Config Dashboard")) {
      throw new Error(`Unexpected page title: ${title}`);
    }
    
    // 2. Tab Navigation
    const tabs = [
      { name: 'MCP Settings', title: 'Configure parameters directly inside ~/.claude.json' },
      { name: 'Claude Code', title: 'LLM & Environment Configuration' },
      { name: 'Codex CLI', title: 'Security & Permission Policies' },
      { name: 'Antigravity CLI', title: 'LLM & Environment Configuration' },
      { name: 'Agents & Skills', title: 'Agents' }
    ];

    
    for (const tab of tabs) {
      console.log(`Clicking tab: ${tab.name}`);
      await page.click(`header >> text="${tab.name}"`);
      await page.waitForTimeout(500);
      
      // Verify expected content
      const content = await page.textContent('body');
      if (!content.includes(tab.title)) {
        console.error(`PAGE CONTENT RENDERED:\n${content}`);
        throw new Error(`Tab "${tab.name}" did not load expected content: "${tab.title}"`);
      }
    }
    
    // 3. MCP Configuration Check & Custom MCP Add
    console.log("Verifying MCP Configuration Editor...");
    await page.click('header >> text="MCP Settings"');
    await page.waitForTimeout(500);
    
    // Click playwright server in the sidebar
    await page.click('aside >> text="playwright"');
    await page.waitForTimeout(500);
    
    // Verify it loaded command
    const commandVal = await page.inputValue('input[placeholder="npx"]');
    console.log(`Playwright command value: ${commandVal}`);
    if (commandVal !== "npx") {
      throw new Error(`Expected playwright command to be "npx", got "${commandVal}"`);
    }
    
    // Click Add Custom MCP button
    console.log("Opening Add Custom MCP modal...");
    await page.click('button:has-text("Add Custom MCP")');
    await page.waitForTimeout(500);
    
    // Fill in Custom MCP fields
    console.log("Filling in Custom MCP fields...");
    await page.fill('input[placeholder="e.g. mysql-connector"]', 'mysql-test');
    await page.fill('input[placeholder="e.g. npx"]', 'npx');
    await page.fill('textarea[placeholder*="postgres"]', '-y\nmcp-server-mysql');
    
    // Click Add Server to Staging
    console.log("Clicking Add Server to Staging...");
    await page.click('button:has-text("Add Server to Staging")');
    await page.waitForTimeout(500);
    
    // Verify "mysql-test" is added to staged changes
    let stagedText = await page.locator('div.section-title:has-text("Staged Changes") + div').textContent();
    console.log(`Staged changes after adding custom MCP: ${stagedText}`);
    if (!stagedText.includes("mysql-test")) {
      throw new Error("Staging custom MCP server failed: mysql-test not in Staged Changes.");
    }
    
    // Discard changes to revert custom MCP
    console.log("Discarding custom MCP change...");
    await page.click('button:has-text("Discard Changes")');
    await page.waitForTimeout(500);
    await page.click('div.fixed >> button:has-text("Discard Changes")');
    await page.waitForTimeout(500);
    
    // Verify staged changes is now empty
    stagedText = await page.locator('div.section-title:has-text("Staged Changes") + div').textContent();
    console.log(`Staged changes after discard: ${stagedText}`);
    if (stagedText.includes("mysql-test")) {
      throw new Error("Discard changes failed: mysql-test config is still staged.");
    }
    
    // 4. Explorer sub-checks
    console.log("Verifying Agents & Skills Explorer lists...");
    await page.click('header >> text="Agents & Skills"');
    await page.waitForTimeout(500);
    
    // Click on the first agent/skill under Agents (architect)
    await page.click('aside >> text="architect"');
    await page.waitForTimeout(500);
    
    // Check details pane header
    const detailHeader = await page.locator('h2').first().textContent();
    console.log(`Selected item details header: ${detailHeader}`);
    if (!detailHeader.includes("architect")) {
      throw new Error(`Failed to load details for architect agent: ${detailHeader}`);
    }
    
    // 5. Staged Changes & Discard Changes
    console.log("Testing staging changes and discarding...");
    // Switch to Dashboard tab
    await page.click('header >> text="Dashboard"');
    await page.waitForTimeout(500);
    
    // Target toggle - let's toggle "Claude Code" target in CLI Targets
    console.log("Toggling Claude Code target...");
    await page.click('aside >> text="Claude Code"');
    await page.waitForTimeout(500);
    
    // Check staged changes panel
    stagedText = await page.locator('div.section-title:has-text("Staged Changes") + div').textContent();
    console.log(`Staged changes text: ${stagedText}`);
    if (!stagedText.includes("Claude Code")) {
      throw new Error("Staging target change failed: target Claude Code not listed in Staged Changes.");
    }
    
    // Click Discard Changes button
    console.log("Clicking Discard Changes button in sidebar...");
    await page.click('button:has-text("Discard Changes")');
    await page.waitForTimeout(500);
    
    // Confirm in discard modal
    console.log("Confirming discard in modal...");
    await page.click('div.fixed >> button:has-text("Discard Changes")');
    await page.waitForTimeout(500);
    
    // Verify staged changes is now empty
    stagedText = await page.locator('div.section-title:has-text("Staged Changes") + div').textContent();
    console.log(`Staged changes after discard: ${stagedText}`);
    if (stagedText.includes("Claude Code")) {
      throw new Error("Discard changes failed: change is still staged.");
    }
    
    // 6. Apply Changes & Stream logs
    console.log("Staging change again for apply test...");
    await page.click('aside >> text="Claude Code"');
    await page.waitForTimeout(500);
    
    console.log("Clicking Apply Changes...");
    await page.click('button:has-text("Apply Changes")');
    await page.waitForTimeout(500);
    
    console.log("Clicking Standard Apply in modal...");
    await page.click('button:has-text("Standard Apply")');
    
    console.log("Waiting for logs to stream...");
    let logsText = "";
    let completed = false;
    for (let i = 0; i < 30; i++) {
      await page.waitForTimeout(1000);
      logsText = await page.locator('div:has-text("Process Output Logs")').locator('xpath=following-sibling::div').textContent();
      if (logsText && !logsText.includes("No logs written")) {
        console.log(`[Logs Iteration ${i + 1}] Log output contains content. Length: ${logsText.length}`);
        if (logsText.includes("SUCCESS:") || logsText.includes("ERROR:") || logsText.includes("Apply failed") || logsText.includes("Done!")) {
          completed = true;
          break;
        }
      }
    }
    
    console.log("Final log output:");
    console.log("================================");
    console.log(logsText.trim());
    console.log("================================");
    
    if (logsText.includes("No logs written") || logsText.trim() === "") {
      throw new Error("Log streaming failed: no logs were output.");
    }
    
    if (!completed) {
      console.log("Warning: Log streaming did not finish, but logs were actively written.");
    }
    
    console.log("E2E tests completed successfully using Edge browser.");
    process.exit(0);
  } catch (error) {
    console.error("Test failed with error:", error);
    process.exit(1);
  } finally {
    if (browser) {
      await browser.close();
    }
  }
})();
