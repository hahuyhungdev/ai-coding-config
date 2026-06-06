const fs = require("fs");
const path = require("path");

const repoConfigPath = process.argv[2];
const userConfigPath = process.argv[3];

if (!repoConfigPath || !userConfigPath) {
    console.error("Usage: node merge-toml-config.js <source-config> <target-config>");
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

function parseTOML(content) {
    const lines = content.split(/\r?\n/);
    const root = {};
    let currentTable = null;

    for (let line of lines) {
        line = line.trim();
        if (!line || line.startsWith("#")) {
            continue;
        }

        const tableMatch = line.match(/^\[([^\]]+)\]$/);
        if (tableMatch) {
            currentTable = tableMatch[1].trim();
            if (!root[currentTable]) {
                root[currentTable] = {};
            }
            continue;
        }

        const kvMatch = line.match(/^([^=]+)=\s*(.+)$/);
        if (kvMatch) {
            const key = kvMatch[1].trim();
            const val = kvMatch[2].trim();
            if (currentTable) {
                root[currentTable][key] = val;
            } else {
                root[key] = val;
            }
        }
    }
    return root;
}

function stringifyTOML(obj) {
    let result = "";

    for (const key of Object.keys(obj)) {
        if (typeof obj[key] !== "object") {
            result += `${key} = ${obj[key]}\n`;
        }
    }
    result += "\n";

    for (const key of Object.keys(obj)) {
        if (typeof obj[key] === "object") {
            result += `[${key}]\n`;
            for (const subKey of Object.keys(obj[key])) {
                result += `${subKey} = ${obj[key][subKey]}\n`;
            }
            result += "\n";
        }
    }
    return result;
}

try {
    const repoContent = fs.readFileSync(repoConfigPath, "utf8");
    const userContent = fs.readFileSync(userConfigPath, "utf8");

    const repoObj = parseTOML(repoContent);
    const userObj = parseTOML(userContent);

    const mergedObj = { ...userObj };

    // Remove disabled mcp_servers from both repo and user configs
    for (const name of sharedDisabled) {
        const serverKey = `mcp_servers.${name}`;
        delete repoObj[serverKey];
        delete mergedObj[serverKey];
    }

    // Remove URL-based mcp_servers from repo (Codex only supports stdio)
    for (const key of Object.keys(repoObj)) {
        if (key.startsWith("mcp_servers.") && typeof repoObj[key] === "object" && repoObj[key].url) {
            delete repoObj[key];
        }
    }

    for (const key of Object.keys(repoObj)) {
        if (typeof repoObj[key] === "object") {
            if (!mergedObj[key]) {
                mergedObj[key] = { ...repoObj[key] };
            } else {
                if (key === "mcp_servers" || key.startsWith("mcp_servers.")) {
                    // For mcp_servers, we always prefer repo's definition to fix broken/outdated command/args
                    mergedObj[key] = { ...mergedObj[key], ...repoObj[key] };
                } else {
                    // Merge keys inside table, preferring user's existing keys
                    mergedObj[key] = { ...repoObj[key], ...mergedObj[key] };
                }
            }
        } else {
            if (mergedObj[key] === undefined) {
                mergedObj[key] = repoObj[key];
            }
        }
    }

    const mergedContent = stringifyTOML(mergedObj);
    fs.writeFileSync(userConfigPath, mergedContent, "utf8");
    console.log("Successfully merged Codex configuration into " + userConfigPath);
} catch (err) {
    console.error("Failed to merge Codex config:", err.message);
    process.exit(1);
}
