const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const srcAgentsDir = path.join(repoRoot, "agents");
const claudeAgentsDir = path.join(repoRoot, "claude", "agents");
const codexAgentsDir = path.join(repoRoot, "codex", "agents");

// Helper to parse YAML frontmatter (custom parser to avoid external dependencies)
function parseFrontmatter(text) {
    const lines = text.split(/\r?\n/);
    const meta = {};
    let codexMeta = null;
    let inCodex = false;

    for (let line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith("#")) continue;

        // Check if we are inside the nested codex: block
        if (inCodex) {
            // If the line is indented, it belongs to codex
            if (line.startsWith(" ") || line.startsWith("\t")) {
                const indentMatch = trimmed.match(/^([a-zA-Z0-9_-]+):\s*(.*)$/);
                if (indentMatch) {
                    if (!codexMeta) codexMeta = {};
                    const key = indentMatch[1].trim();
                    const val = indentMatch[2].trim().replace(/^['"]|['"]$/g, ""); // strip quotes
                    codexMeta[key] = val;
                    continue;
                }
            } else {
                inCodex = false;
            }
        }

        const match = trimmed.match(/^([a-zA-Z0-9_-]+):\s*(.*)$/);
        if (match) {
            const key = match[1].trim();
            const val = match[2].trim();
            if (key === "codex") {
                inCodex = true;
            } else {
                meta[key] = val.replace(/^['"]|['"]$/g, ""); // strip quotes
            }
        }
    }
    if (codexMeta) {
        meta.codex = codexMeta;
    }
    return meta;
}

try {
    // Ensure output directories exist
    fs.mkdirSync(claudeAgentsDir, { recursive: true });
    fs.mkdirSync(codexAgentsDir, { recursive: true });

    // Clean existing compiled files
    const cleanDir = (dir) => {
        if (fs.existsSync(dir)) {
            for (const file of fs.readdirSync(dir)) {
                fs.unlinkSync(path.join(dir, file));
            }
        }
    };
    cleanDir(claudeAgentsDir);
    cleanDir(codexAgentsDir);

    const files = fs.readdirSync(srcAgentsDir).filter(f => f.endsWith(".md"));
    console.log(`Found ${files.length} agent source files. Starting compilation...`);

    for (const file of files) {
        const filePath = path.join(srcAgentsDir, file);
        const content = fs.readFileSync(filePath, "utf8");
        const name = path.basename(file, ".md");

        const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);
        if (!match) {
            console.warn(`[WARN] Skipping ${file} due to missing frontmatter`);
            continue;
        }

        const frontmatterText = match[1];
        const body = match[2];
        const meta = parseFrontmatter(frontmatterText);

        // 1. Generate Claude / agy Agent (Markdown)
        let claudeFrontmatter = "---\n";
        for (const key of Object.keys(meta)) {
            if (key !== "codex") {
                claudeFrontmatter += `${key}: ${meta[key]}\n`;
            }
        }
        claudeFrontmatter += "---\n";
        const claudeContent = claudeFrontmatter + body;
        fs.writeFileSync(path.join(claudeAgentsDir, `${name}.md`), claudeContent, "utf8");

        // 2. Generate Codex Agent (TOML)
        // Determine default values based on Claude model tier
        let codexModel = "gpt-5.5";
        let codexReasoning = "high";
        let codexSandbox = "workspace-write";

        if (meta.model === "sonnet") {
            codexReasoning = "medium";
        } else if (meta.model === "haiku") {
            codexReasoning = "low";
            codexSandbox = "read-only";
        }

        // Apply overrides from YAML codex block if available
        if (meta.codex) {
            if (meta.codex.model) codexModel = meta.codex.model;
            if (meta.codex.model_reasoning_effort) codexReasoning = meta.codex.model_reasoning_effort;
            if (meta.codex.sandbox_mode) codexSandbox = meta.codex.sandbox_mode;
        }

        let tomlContent = `model = "${codexModel}"\n`;
        tomlContent += `model_reasoning_effort = "${codexReasoning}"\n`;
        tomlContent += `sandbox_mode = "${codexSandbox}"\n\n`;
        tomlContent += `description = "${meta.description || ""}"\n\n`;
        tomlContent += `developer_instructions = """\n${body.trim()}\n"""\n`;

        fs.writeFileSync(path.join(codexAgentsDir, `${name}.toml`), tomlContent, "utf8");
    }

    console.log("Agent compilation complete!");
} catch (err) {
    console.error("Compilation failed:", err.message);
    process.exit(1);
}
