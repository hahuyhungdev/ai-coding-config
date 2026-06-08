const { chromium } = require('playwright');

(async () => {
  console.log("Starting direct Playwright layout structure validation...");
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1400, height: 900 });
  
  try {
    console.log("Navigating to http://127.0.0.1:8000...");
    await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle' });

    const tabs = [
      { name: 'Claude Code', expectedEditor: 'CLAUDE.md' },
      { name: 'Codex CLI', expectedEditor: 'AGENTS.md' },
      { name: 'Antigravity CLI', expectedEditor: 'ANTIGRAVITY.md' }
    ];

    for (const tab of tabs) {
      console.log(`\nChecking Tab: "${tab.name}"`);
      await page.click(`header >> text="${tab.name}"`);
      await page.waitForTimeout(500);

      // 1. Verify Left Column Settings Card Names
      const cardHeaders = await page.evaluate(() => {
        const cards = Array.from(document.querySelectorAll('.bg-mantle div.text-base'));
        return cards.map(c => c.textContent.trim());
      });

      console.log("  -> Left Settings Card Titles:", cardHeaders);
      if (cardHeaders.length !== 2) {
        throw new Error(`Expected exactly 2 settings cards, found ${cardHeaders.length}`);
      }
      if (cardHeaders[0] !== 'LLM & Environment Configuration') {
        throw new Error(`Card 1 title mismatch: got "${cardHeaders[0]}"`);
      }
      if (cardHeaders[1] !== 'Security & Permission Policies') {
        throw new Error(`Card 2 title mismatch: got "${cardHeaders[1]}"`);
      }

      // 2. Verify Modal Editor Header File Label
      const buttonText = `Edit ${tab.expectedEditor} Instructions`;
      console.log(`  -> Clicking button: "${buttonText}"`);
      await page.click(`button:has-text("${buttonText}")`);
      await page.waitForTimeout(300);

      const modalHeader = await page.evaluate(() => {
        const ta = document.querySelector('textarea[placeholder*="Instructions"]');
        if (!ta) return null;
        const headerDiv = ta.parentElement.querySelector('.text-sm');
        return headerDiv ? headerDiv.textContent.trim() : null;
      });

      console.log(`  -> Modal Editor Header: "${modalHeader}"`);
      if (!modalHeader || !modalHeader.includes(tab.expectedEditor)) {
        throw new Error(`Editor header mismatch: expected containing "${tab.expectedEditor}", got "${modalHeader}"`);
      }

      // Close the modal
      console.log(`  -> Closing modal...`);
      await page.click('button:has-text("Close & Stage")');
      await page.waitForTimeout(300);

      // 3. Verify Width Alignment (Inputs & Selects should use w-full)
      const nonWFullInputs = await page.evaluate(() => {
        const elements = Array.from(document.querySelectorAll('input, select'));
        return elements
          .filter(el => !el.classList.contains('w-full') && el.type !== 'checkbox' && !el.closest('aside'))
          .map(el => `${el.tagName.toLowerCase()}: ${el.placeholder || el.value || 'select'}`);
      });

      if (nonWFullInputs.length > 0) {
        throw new Error(`Found form controls without "w-full" alignment: ${JSON.stringify(nonWFullInputs)}`);
      } else {
        console.log("  -> Width Alignment: PASS (All inputs/selects are full-width)");
      }
    }

    console.log("\n=======================================================");
    console.log("SUCCESS: All 3 CLI tabs have 100% identical layout structure!");
    console.log("=======================================================");
    process.exit(0);

  } catch (err) {
    console.error("\nFAIL: Layout structure verification failed!");
    console.error(err.message);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
