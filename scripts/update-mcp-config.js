const fs = require("fs");
const path = require("path");

const file = process.argv[2];

if (!file) {
    console.error("Usage: node update-mcp-config.js <config-json-path>");
    process.exit(1);
}

// Read shared disabled list
const sharedDisabledPath = path.join(__dirname, "..", "shared-disabled-mcp.json");
let sharedDisabled = [];
try {
    const shared = JSON.parse(fs.readFileSync(sharedDisabledPath, "utf8"));
    sharedDisabled = shared.disabledMcpServers || [];
} catch (e) {
    // No shared config, that's fine
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
            args: ["-y", "@playwright/mcp@latest", "--browser", "msedge", "--headless", "--ignore-https-errors", "--isolated", "--output-dir", ".playwright-mcp"]
        },
        context7: {
            type: "sse",
            url: "https://mcp.context7.com/mcp"
        },
        memory: {
            command: "npx",
            args: ["-y", "@modelcontextprotocol/server-memory"]
        },
        "sequential-thinking": {
            command: "npx",
            args: ["-y", "@modelcontextprotocol/server-sequential-thinking"]
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

    const disabledObj = data.disabledMcpServers || {};
    const disabled = new Set([...Object.keys(disabledObj), ...sharedDisabled]);

    let updated = false;

    // Remove servers that are now disabled
    for (const name of disabled) {
        if (data.mcpServers[name]) {
            delete data.mcpServers[name];
            console.log("Removed disabled server: " + name + " from " + file);
            updated = true;
        }
    }

    // Add or update default servers (skip disabled ones)
    for (const [name, config] of Object.entries(defaultServers)) {
        // Skip servers that user has explicitly disabled
        if (disabled.has(name)) {
            continue;
        }
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
                const oIdx = args.indexOf("--output-dir");
                if (oIdx === -1) {
                    args.push("--output-dir", ".playwright-mcp");
                    pUpdated = true;
                } else if (oIdx + 1 < args.length && args[oIdx + 1] !== ".playwright-mcp") {
                    args[oIdx + 1] = ".playwright-mcp";
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
