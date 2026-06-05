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
    const defaultServers = {
        playwright: {
            command: "npx",
            args: ["-y", "@playwright/mcp@latest", "--browser", "msedge", "--headless", "--ignore-https-errors", "--isolated"]
        },
        postgres: {
            command: "npx",
            args: ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/postgres"]
        },
        sqlite: {
            command: "npx",
            args: ["-y", "mcp-server-sqlite", "--db", "database.db"]
        },
        docker: {
            command: "npx",
            args: ["-y", "mcp-server-docker"]
        },
        aws: {
            command: "uvx",
            args: ["awslabs.aws-api-mcp-server@latest"]
        }
    };

    let updated = false;

    for (const [name, config] of Object.entries(defaultServers)) {
        if (!data.mcpServers[name]) {
            data.mcpServers[name] = config;
            console.log("Initialized " + name + " MCP in " + file);
            updated = true;
        } else {
            // Check playwright configuration details
            if (name === "playwright") {
                const args = data.mcpServers.playwright.args || [];
                let pUpdated = false;
                if (!args.includes("--isolated")) {
                    args.push("--isolated");
                    pUpdated = true;
                }
                const bIdx = args.indexOf("--browser");
                if (bIdx !== -1 && bIdx + 1 < args.length && args[bIdx + 1] !== "msedge") {
                    args[bIdx + 1] = "msedge";
                    pUpdated = true;
                }
                if (pUpdated) {
                    data.mcpServers.playwright.args = args;
                    console.log("Updated playwright MCP in " + file);
                    updated = true;
                }
            }
        }
    }

    if (updated) {
        fs.writeFileSync(file, JSON.stringify(data, null, 2), "utf8");
    }
} catch (e) {
    console.error("Error updating " + file + ":", e.message);
}
