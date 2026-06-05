const fs = require("fs");

const file = process.argv[2];

if (!file) {
    console.error("Usage: node update-mcp-config.js <config-json-path>");
    process.exit(1);
}

try {
    let data = {};
    const content = fs.readFileSync(file, "utf8").trim();
    if (content) {
        data = JSON.parse(content);
    }
    if (!data.mcpServers) {
        data.mcpServers = {};
    }
    if (!data.mcpServers.playwright) {
        data.mcpServers.playwright = {
            command: "npx",
            args: ["-y", "@playwright/mcp@latest", "--browser", "chromium", "--headless", "--ignore-https-errors", "--isolated"]
        };
        fs.writeFileSync(file, JSON.stringify(data, null, 2), "utf8");
        console.log("Initialized playwright MCP in " + file);
    } else {
        const args = data.mcpServers.playwright.args || [];
        if (!args.includes("--isolated")) {
            args.push("--isolated");
            data.mcpServers.playwright.args = args;
            fs.writeFileSync(file, JSON.stringify(data, null, 2), "utf8");
            console.log("Added --isolated to " + file);
        }
    }
} catch (e) {
    console.error("Error updating " + file + ":", e.message);
}
