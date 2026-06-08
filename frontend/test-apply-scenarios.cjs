const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const REPO_DIR = path.resolve(__dirname, '..');
const HOME = process.env.HOME || '/home/huyhung';

// Global destinations to backup/restore
const BACKUP_FILES = {
  claude_settings: path.join(HOME, '.claude', 'settings.json'),
  claude_md: path.join(HOME, '.claude', 'CLAUDE.md'),
  claude_rtk: path.join(HOME, '.claude', 'RTK.md'),
  codex_config: path.join(HOME, '.codex', 'config.toml'),
  codex_agents: path.join(HOME, '.codex', 'AGENTS.md'),
  codex_rtk: path.join(HOME, '.codex', 'RTK.md'),
  gemini_settings: path.join(HOME, '.gemini', 'antigravity-cli', 'settings.json'),
  gemini_md: path.join(HOME, '.gemini', 'config', 'ANTIGRAVITY.md')
};

// Repository template files
const TEMPLATES = {
  claude_settings: path.join(REPO_DIR, 'claude', 'settings.json'),
  claude_md: path.join(REPO_DIR, 'claude', 'CLAUDE.md'),
  codex_config: path.join(REPO_DIR, 'codex', 'config.toml'),
  gemini_settings: path.join(REPO_DIR, 'gemini', 'settings.json')
};

(async () => {
  console.log("=======================================================");
  console.log("STARTING COMPREHENSIVE INTEGRATION & APPLY TESTING");
  console.log("=======================================================");
  
  let browser;
  const backups = {};
  const originalTemplates = {};
  let exitCode = 0;

  try {
    // 1. Back up templates in repository
    console.log("Backing up local repository template files...");
    for (const [key, filePath] of Object.entries(TEMPLATES)) {
      if (fs.existsSync(filePath)) {
        originalTemplates[key] = fs.readFileSync(filePath, 'utf8');
      }
    }

    // 2. Back up and temporarily remove global files (to avoid conflicts in Scenario 1)
    console.log("Backing up and removing global config files to ensure a clean test environment...");
    for (const [key, filePath] of Object.entries(BACKUP_FILES)) {
      if (fs.existsSync(filePath)) {
        backups[key] = fs.readFileSync(filePath, 'utf8');
        console.log(`  -> Backed up: ${filePath}`);
        // Remove file to prevent conflict on standard apply
        fs.unlinkSync(filePath);
      }
    }

    browser = await chromium.launch({ channel: 'msedge', headless: true });
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await context.newPage();
    
    console.log("Navigating to dashboard...");
    await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle' });

    // --- SCENARIO 1: EDIT SETTINGS & APPLY ---
    console.log("\n--- SCENARIO 1: Edit Settings on Web & Run Standard Apply ---");
    
    // 1. Edit Claude Code Configuration
    console.log("Navigating to Claude Code tab...");
    await page.click('button:has-text("Claude Code")');
    await page.waitForTimeout(300);
    console.log("Changing Max Thinking Tokens to 25000...");
    await page.fill('input[value="20000"]', '25000');
    
    // Open instructions modal
    console.log("Opening Claude.md instructions modal...");
    await page.click('button:has-text("Edit CLAUDE.md Instructions")');
    await page.waitForTimeout(300);
    // Append test rules
    const currentInst = await page.inputValue('textarea[placeholder*="Instructions"]');
    await page.fill('textarea[placeholder*="Instructions"]', currentInst + '\n\n## Custom Test Rules Added');
    console.log("Closing and staging instructions modal...");
    await page.click('button:has-text("Close & Stage")');
    await page.waitForTimeout(300);

    // 2. Edit Codex CLI Configuration
    console.log("Navigating to Codex CLI tab...");
    await page.click('button:has-text("Codex CLI")');
    await page.waitForTimeout(300);
    console.log("Changing Model Alias to gpt-6.0-ultra...");
    await page.fill('input[value="gpt-5.5"]', 'gpt-6.0-ultra');

    // 3. Edit Antigravity CLI Configuration
    console.log("Navigating to Antigravity CLI tab...");
    await page.click('button:has-text("Antigravity CLI")');
    await page.waitForTimeout(300);
    console.log("Changing Model Alias to Gemini 4.0 Pro...");
    await page.fill('input[value="Gemini 3.5 Flash (High)"]', 'Gemini 4.0 Pro');

    // Verify staged changes in sidebar
    const stagedText = await page.locator('div.section-title:has-text("Staged Changes") + div').textContent();
    console.log(`Staged changes in sidebar:\n${stagedText}`);
    
    if (!stagedText.includes("MAX_THINKING_TOKENS") || !stagedText.includes("gpt-6.0-ultra") || !stagedText.includes("Gemini 4.0 Pro") || !stagedText.includes("CLAUDE.md")) {
      throw new Error("Staged changes do not list all edited parameters!");
    }

    // Apply Changes via Standard Apply
    console.log("Applying changes via Standard Apply...");
    await page.click('button:has-text("Apply Changes")');
    await page.waitForTimeout(300);
    await page.click('button:has-text("Standard Apply")');
    
    console.log("Waiting for installation logs to finish...");
    let logsText = "";
    let completed = false;
    for (let i = 0; i < 30; i++) {
      await page.waitForTimeout(1000);
      logsText = await page.locator('div:has-text("Process Output Logs")').locator('xpath=following-sibling::div').textContent();
      if (logsText.includes("SUCCESS:") || logsText.includes("ERROR:") || logsText.includes("Done!")) {
        completed = true;
        break;
      }
    }
    console.log("Installation output log summary:");
    console.log(logsText.trim().split('\n').slice(-5).join('\n'));

    if (!completed || !logsText.includes("SUCCESS:")) {
      throw new Error("Standard Apply failed or timed out!");
    }

    // Verify files on disk have the new configs
    console.log("\nVerifying files on disk...");
    
    // Check Claude template and global file
    const claudeJson = JSON.parse(fs.readFileSync(TEMPLATES.claude_settings, 'utf8'));
    console.log(`  -> Claude Template MAX_THINKING_TOKENS: ${claudeJson.env.MAX_THINKING_TOKENS}`);
    if (claudeJson.env.MAX_THINKING_TOKENS !== "25000") {
      throw new Error(`Expected MAX_THINKING_TOKENS to be "25000", got "${claudeJson.env.MAX_THINKING_TOKENS}"`);
    }

    const claudeMd = fs.readFileSync(BACKUP_FILES.claude_md, 'utf8');
    if (!claudeMd.includes("## Custom Test Rules Added")) {
      throw new Error("CLAUDE.md global instructions file was not compiled/synchronized!");
    }
    console.log("  -> CLAUDE.md synchronized: PASS");

    // Check Codex template
    const codexToml = fs.readFileSync(TEMPLATES.codex_config, 'utf8');
    if (!codexToml.includes('model = "gpt-6.0-ultra"')) {
      throw new Error("Codex model was not updated in config.toml template!");
    }
    console.log("  -> Codex config.toml model update: PASS");

    // Check Gemini template
    const geminiJson = JSON.parse(fs.readFileSync(TEMPLATES.gemini_settings, 'utf8'));
    if (geminiJson.model !== "Gemini 4.0 Pro") {
      throw new Error(`Expected Gemini model to be "Gemini 4.0 Pro", got "${geminiJson.model}"`);
    }
    console.log("  -> Gemini settings.json model update: PASS");


    // --- SCENARIO 2: CONFLICT DETECTION & BYPASS ---
    console.log("\n--- SCENARIO 2: Conflict Detection & Non-Interactive Bypass ---");
    
    // Introduce a manual change in global settings to trigger conflict
    console.log("Simulating conflict in global settings.json...");
    const currentGlobalClaude = JSON.parse(fs.readFileSync(BACKUP_FILES.claude_settings, 'utf8'));
    currentGlobalClaude.manual_conflict_trigger = "manual-value-123";
    fs.writeFileSync(BACKUP_FILES.claude_settings, JSON.stringify(currentGlobalClaude, null, 2));

    // Change something on the web tab to trigger another apply
    console.log("Changing Max Thinking Tokens to 26000 on Web...");
    await page.click('button:has-text("Claude Code")');
    await page.waitForTimeout(300);
    await page.fill('input[value="25000"]', '26000');
    
    // Apply Changes via Standard Apply (conflict should be skipped since stdin=DEVNULL)
    console.log("Applying changes via Standard Apply...");
    await page.click('button:has-text("Apply Changes")');
    await page.waitForTimeout(300);
    await page.click('button:has-text("Standard Apply")');

    completed = false;
    for (let i = 0; i < 30; i++) {
      await page.waitForTimeout(1000);
      logsText = await page.locator('div:has-text("Process Output Logs")').locator('xpath=following-sibling::div').textContent();
      if (logsText.includes("SUCCESS:") || logsText.includes("ERROR:") || logsText.includes("Done!")) {
        completed = true;
        break;
      }
    }
    console.log("Standard Apply output containing conflict check:");
    console.log(logsText.trim().split('\n').filter(line => line.includes("Conflict") || line.includes("Skipping") || line.includes("SUCCESS")).join('\n'));

    // The apply should succeed, but skip settings.json
    if (!completed || !logsText.includes("SUCCESS:")) {
      throw new Error("Standard Apply failed to complete cleanly when conflict was skipped!");
    }

    // Verify global settings.json still has the manual change (skipped copy)
    const afterSkipClaudeGlobal = JSON.parse(fs.readFileSync(BACKUP_FILES.claude_settings, 'utf8'));
    if (afterSkipClaudeGlobal.manual_conflict_trigger !== "manual-value-123") {
      throw new Error("Conflict was overwritten during Standard Apply! Skip failed.");
    }
    console.log("  -> Conflict Skipped and original settings.json preserved: PASS");

    // Apply Changes via Force Overwrite (conflict should be overwritten)
    console.log("\nApplying changes via Force Overwrite...");
    // Let's modify Max Thinking Tokens to make sure there are staged changes to apply
    await page.click('button:has-text("Claude Code")');
    await page.waitForTimeout(300);
    await page.fill('input[value="26000"]', '27000');
    await page.waitForTimeout(300);

    await page.click('button:has-text("Apply Changes")');
    await page.waitForTimeout(300);
    await page.click('button:has-text("Force Overwrite")');

    completed = false;
    for (let i = 0; i < 30; i++) {
      await page.waitForTimeout(1000);
      logsText = await page.locator('div:has-text("Process Output Logs")').locator('xpath=following-sibling::div').textContent();
      if (logsText.includes("SUCCESS:") || logsText.includes("ERROR:") || logsText.includes("Done!")) {
        completed = true;
        break;
      }
    }
    console.log("Force Apply output logs:");
    console.log(logsText.trim().split('\n').filter(line => line.includes("Overwritten") || line.includes("SUCCESS")).join('\n'));

    if (!completed || !logsText.includes("SUCCESS:")) {
      throw new Error("Force Apply failed or timed out!");
    }

    // Verify global settings.json has been overwritten (manual change is gone)
    const afterForceClaudeGlobal = JSON.parse(fs.readFileSync(BACKUP_FILES.claude_settings, 'utf8'));
    if (afterForceClaudeGlobal.manual_conflict_trigger === "manual-value-123") {
      throw new Error("Conflict was NOT overwritten during Force Overwrite! Force failed.");
    }
    console.log("  -> Conflict Overwritten during Force Overwrite: PASS");

    console.log("\n=======================================================");
    console.log("SUCCESS: All apply scenarios verified successfully!");
    console.log("=======================================================");

  } catch (err) {
    console.error("\nFAIL: Apply integration testing failed!");
    console.error(err);
    exitCode = 1;
  } finally {
    // Restore templates
    console.log("\nRestoring repository template files...");
    for (const [key, content] of Object.entries(originalTemplates)) {
      const filePath = TEMPLATES[key];
      fs.writeFileSync(filePath, content);
      console.log(`  -> Restored template: ${filePath}`);
    }

    // Restore global configuration files
    console.log("Restoring original global config files...");
    for (const [key, filePath] of Object.entries(BACKUP_FILES)) {
      const dirPath = path.dirname(filePath);
      if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath, { recursive: true });
      }
      if (backups[key] !== undefined) {
        fs.writeFileSync(filePath, backups[key]);
        console.log(`  -> Restored global: ${filePath}`);
      } else if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
        console.log(`  -> Removed temp global: ${filePath}`);
      }
    }

    if (browser) {
      await browser.close();
    }
    process.exit(exitCode);
  }
})();
