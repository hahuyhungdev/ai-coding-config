const fs = require("fs");
const path = require("path");
const os = require("os");

const repoRoot = path.resolve(__dirname, "..");
const srcAgentsDir = path.join(repoRoot, "agents");

const homeDir = os.homedir();
const claudeAgentsDir = path.join(homeDir, ".claude", "agents");
const codexAgentsDir = path.join(homeDir, ".codex", "agents");
const agyAgentsDir = path.join(homeDir, ".gemini", "config", "agents");

// Parse arguments
const args = process.argv.slice(2);
let compileClaude = false;
let compileCodex = false;
let compileAgy = false;

if (args.length === 0 || args.includes("--all")) {
    compileClaude = true;
    compileCodex = true;
    compileAgy = true;
} else {
    if (args.includes("--claude")) compileClaude = true;
    if (args.includes("--codex")) compileCodex = true;
    if (args.includes("--agy")) compileAgy = true;
}

// Helper to parse YAML frontmatter
function parseFrontmatter(text) {
    const lines = text.split(/\r?\n/);
    const meta = {};
    let codexMeta = null;
    let inCodex = false;

    for (let line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith("#")) continue;

        if (inCodex) {
            if (line.startsWith(" ") || line.startsWith("\t")) {
                const indentMatch = trimmed.match(/^([a-zA-Z0-9_-]+):\s*(.*)$/);
                if (indentMatch) {
                    if (!codexMeta) codexMeta = {};
                    const key = indentMatch[1].trim();
                    const val = indentMatch[2].trim().replace(/^['"]|['"]$/g, "");
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
                meta[key] = val.replace(/^['"]|['"]$/g, "");
            }
        }
    }
    if (codexMeta) {
        meta.codex = codexMeta;
    }
    return meta;
}

// Helper to ensure target directory is a clean, real directory
function ensureCleanDir(dir) {
    try {
        const lstat = fs.lstatSync(dir);
        if (lstat.isSymbolicLink()) {
            fs.unlinkSync(dir);
        } else if (lstat.isDirectory()) {
            for (const file of fs.readdirSync(dir)) {
                fs.unlinkSync(path.join(dir, file));
            }
            return;
        } else {
            fs.unlinkSync(dir);
        }
    } catch (e) {
        // Directory doesn't exist
    }
    fs.mkdirSync(dir, { recursive: true });
}

try {
    // Ensure target directories exist and compile agents if enabled
    if (compileClaude) {
        ensureCleanDir(claudeAgentsDir);
        console.log(`Writing Claude agents directly to: ${claudeAgentsDir}`);
    }
    if (compileCodex) {
        ensureCleanDir(codexAgentsDir);
        console.log(`Writing Codex agents directly to: ${codexAgentsDir}`);
    }
    if (compileAgy) {
        ensureCleanDir(agyAgentsDir);
        console.log(`Writing agy agents directly to: ${agyAgentsDir}`);
    }

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

        // 1. Compile Claude Agent (Markdown)
        if (compileClaude) {
            let claudeFrontmatter = "---\n";
            for (const key of Object.keys(meta)) {
                if (key !== "codex") {
                    claudeFrontmatter += `${key}: ${meta[key]}\n`;
                }
            }
            claudeFrontmatter += "---\n";
            const claudeContent = claudeFrontmatter + body;
            fs.writeFileSync(path.join(claudeAgentsDir, `${name}.md`), claudeContent, "utf8");
        }

        // 2. Compile agy Agent (Markdown)
        if (compileAgy) {
            let agyFrontmatter = "---\n";
            for (const key of Object.keys(meta)) {
                if (key !== "codex") {
                    agyFrontmatter += `${key}: ${meta[key]}\n`;
                }
            }
            agyFrontmatter += "---\n";
            const agyContent = agyFrontmatter + body;
            fs.writeFileSync(path.join(agyAgentsDir, `${name}.md`), agyContent, "utf8");
        }

        // 3. Compile Codex Agent (TOML)
        if (compileCodex) {
            let codexModel = "gpt-5.5";
            let codexReasoning = "high";
            let codexSandbox = "workspace-write";

            if (meta.model === "sonnet") {
                codexReasoning = "medium";
            } else if (meta.model === "haiku") {
                codexReasoning = "low";
                codexSandbox = "read-only";
            }

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
    }

    console.log("Agent compilation complete!");
} catch (err) {
    console.error("Compilation failed:", err.message);
    process.exit(1);
}
