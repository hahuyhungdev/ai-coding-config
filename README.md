# 🚀 AI Coding Config Engine

A unified, centralized configuration hub and interactive control center for **Claude Code**, **Codex CLI**, and **Antigravity CLI (agy)**. Manage custom agents, reusable skills, rules (ECC standards), MCP servers, and environment settings in a single repository and synchronize them across your local system.

---

## ✨ Features

- **Multi-CLI Support**: Centralized configs for Claude Code, Codex CLI, and Antigravity CLI (`agy`).
- **Interactive Web Dashboard**: A modern, single-page React app to inspect, edit, stage, and apply configurations.
- **On-Demand Instruction Modals**: View and edit `CLAUDE.md`, `AGENTS.md`, and `ANTIGRAVITY.md` instructions inside popup editors directly inline with system parameters.
- **Copy-based Installation**: Copies configuration files (no symlinks) so local overrides do not affect the repository template.
- **Auto-Merge TOML Configurations**: Updates Codex's `config.toml` safely by merging new agents/MCP servers while preserving your personal settings and trusted projects (`[projects]`).
- **Browser Lock Protection**: Configures Playwright MCP with `--isolated` automatically for all CLIs to avoid browser profile conflicts.

---

## ⚡ Quick Start

Clone this repository and run the installer to link configuration files to their active CLI locations.

### 🐧 Linux & macOS (Git Bash/WSL)
```bash
git clone git@github.com:hahuyhungdev/ai-coding-config.git ~/ai-coding-config
cd ~/ai-coding-config
./install.py
```

### 🪟 Windows (CMD / PowerShell)
Run the wrapper batch script (requires Git Bash to be installed in your PATH):
```cmd
git clone git@github.com:hahuyhungdev/ai-coding-config.git %USERPROFILE%\ai-coding-config
cd %USERPROFILE%\ai-coding-config
install.bat
```

---

## 🖥️ Interactive Web Dashboard

Instead of command-line flags, you can run the built-in Interactive Web Dashboard to visually manage target CLIs, toggle MCP servers, edit instructions templates, and monitor installation logs.

```bash
./run-web.sh
```

Or run directly with Python:
```bash
python3 server.py --port 8000
```

### 🌟 Dashboard Highlights
- **Interactive Configuration**: Toggle active CLI targets and individual MCP servers in real-time.
- **Staged Changes Diff**: View visual git-style diffs of your modifications in the sidebar before writing to disk.
- **System Settings Editors**: Edit parameters for Claude, Codex, and Gemini with inline inputs, selects, and toggles.
- **Instructions Modal Editors**: Access and edit instruction files (`CLAUDE.md`, `AGENTS.md`, `ANTIGRAVITY.md`) on-demand inside popup modal dialogs, leaving configuration pages clean.
- **Agents & Skills Explorer**: Browse through custom agents and skills with automatic markdown rendering and metadata extraction.
- **Real-time Log Stream**: Apply changes and watch the installation process live in the browser's terminal console.

---

## ⚙️ Installation Options

You can install configuration assets for all three CLIs at once, or target specific tools selectively using command-line flags.

| Flag                    | Action                                                                         |
| ----------------------- | ------------------------------------------------------------------------------ |
| `./install.py --all`    | Install configurations for **all** three CLIs (default if no flag is provided) |
| `./install.py --claude` | Configure **Claude Code** only (`~/.claude/` assets and `~/.claude.json`)      |
| `./install.py --codex`  | Configure **Codex CLI** only (`~/.codex/` assets and merging `config.toml`)    |
| `./install.py --agy`    | Configure **Antigravity CLI** only (`~/.gemini/config/` assets)                |
| `./install.py --force`  | Force overwrite all destination files, bypassing interactive TTY warnings      |
| `./install.py -h`       | Display the helper menu                                                        |

---

## 📂 What's Included

| Component                |    Claude Code     |     Codex CLI      | Antigravity CLI (`agy`) |
| :----------------------- | :----------------: | :----------------: | :---------------------: |
| **Context File**         |    `CLAUDE.md`     |    `AGENTS.md`     |    `ANTIGRAVITY.md`     |
| **System Settings**      |  `settings.json`   |   `config.toml`    |    `settings.json`      |
| **Custom Agents**        |    15 MD agents    |   15 TOML agents   |  15 MD agents (synced)  |
| **Advanced Skills**      |     25 skills      |     25 skills      |   25 skills (synced)    |
| **Rules (ECC)**          |      12 rules      |         —          |            —            |
| **Playwright Isolation** | Yes (`--isolated`) | Yes (`--isolated`) |   Yes (`--isolated`)    |

### 🛠️ Configured MCP Servers
All CLIs are automatically integrated with the following Model Context Protocol (MCP) servers:
- `playwright`: Browser automation (running in `--isolated` mode).
- `context7`: Library documentation lookup (Claude & Gemini only).
- `memory`: Persistent knowledge graphs.
- `sequential-thinking`: Step-by-step reasoning support.
- `github`: Repository management, issues, and PR interactions (Codex only).

---

## 📁 Repository Structure

```
ai-coding-config/
├── agents/                  # Source of Truth: 15 Custom Agents (.md with YAML frontmatter)
├── skills/                  # Source of Truth: 25 shared skill packages
├── claude/                  # Claude-specific configuration files
│   ├── rules/ecc/           # 12 Engineer Agentic Coding (ECC) rules
│   ├── CLAUDE.md            # Claude Code instructions
│   ├── RTK.md               # Claude Code token optimization reference
│   └── settings.json        # Claude settings & Playwright config
├── codex/                   # Codex-specific configuration files
│   ├── AGENTS.md            # Codex instructions
│   ├── RTK.md               # Codex token optimization reference
│   └── config.toml          # Shared Codex config template
├── gemini/                  # Antigravity-specific configuration files
│   ├── ANTIGRAVITY.md       # Antigravity instructions
│   └── settings.json        # Antigravity settings template
├── scripts/                 # Build & management scripts
│   ├── compile-agents.js    # Compiler script that parses root agents to target folders
│   ├── merge-toml-config.js # Merges Codex config.toml
│   ├── update-mcp-config.js # Updates JSON MCP configs
│   └── mcp-toggle.py        # Toggle MCP servers on/off across all CLIs
├── shared-disabled-mcp.json # Source of truth for disabled MCP servers
├── install.py               # Main installation Python script
├── run-web.sh               # Starts the Interactive Web Dashboard
├── server.py                # Python web backend (FastAPI/SSE)
└── README.md
```

---

## 🛠️ How it Works under the Hood

### 🔗 Copy-based Installation
The installer copies config files from the repo to global locations (`~/.claude`, `~/.codex`, `~/.gemini`). This ensures global edits don't affect the repository.

### ⚡ Conflict Detection
When config files differ between the repository templates and the global destination files:
- **Standard Apply**: In interactive mode, shows a diff and prompts you to Overwrite, Keep, or Skip. In non-interactive mode (e.g. running from the web server), it automatically skips conflicting files with a warning to protect custom local modifications.
- **Force Overwrite**: Passes `--force` to overwrite all global files completely without warnings or checks.

### 🔀 Smart TOML Merging
When updating Codex CLI settings, your `~/.codex/config.toml` file is parsed and merged:
- Any newly introduced custom agents or MCP server definitions in this repo are cleanly injected.
- Your local machine-specific settings and trusted projects (`[projects]`) are fully preserved.

---

## 🔍 Graphify Integration & Testing

If the `graphify` CLI is installed, the installer automatically configures **Graphify Git hooks** and registers optimized **project-level hooks** in your workspace root (`.claude/`, `.gemini/`, and `.codex/`):

### 🛡️ Hook Optimization under the Hood
- **Claude & Gemini (Antigravity):** Registers project-level hooks (`PreToolUse` for Claude and `BeforeTool` for Gemini) that execute a highly optimized Python one-liner on `stdin`. The script filters file/directory tool inputs, checks for programming language extensions, filters out config/metadata directories (e.g. `skills/`, `.claude/`, `.gemini/`, `.codex/`, `.git/`, `node_modules/`), and dynamically injects the Graphify instructions only when reading source files. This prevents context pollution and saves tokens on metadata reads.
- **Codex:** Registers a portable `graphify hook-check` hook.

### 🧪 Verification & Test Suite
We provide a native Python test suite to verify the installers, syntax of templates/output files, and hook filtering behavior.

To run the unit tests:
```bash
python3 -m unittest tests/test_config.py
```

To run the integration tests targeting a real repository (`cal.diy`):
```bash
python3 -m unittest tests/test_cal_diy_integration.py
```

The test suite validates:
- Syntactic correctness of configuration files (JSON and TOML).
- Existence and structure of project-level hook configuration files.
- Real subprocess dry-runs of the Python filtering commands in Claude's and Gemini's hooks against multiple test cases (source files, skill files, ignored directories).
- End-to-end integration and behavior of the Python hooks directly inside the cloned `cal.diy` repository.

---

## 📊 Graphify Token Savings Strategy

### The Problem

Without Graphify, Claude answers codebase questions by chaining raw commands:

```
grep -r "auth" --include="*.ts" → 20 matches
  → Read file 1 (5,000 chars)
  → Read file 2 (4,200 chars)
  → Read file 3 (6,800 chars)
  → ... (5-20 files per query)
```

Each query burns **~8,000-50,000 output tokens** reading raw source files.

### The Solution: Scoped Subgraph

With Graphify, Claude runs a single command that returns a pre-built knowledge graph scoped to the question:

```
graphify query "authentication" → { nodes: [...], edges: [...] }
```

**Same answer, ~50-200 tokens.**

### Real Session Comparison

Tested across 28 independent Claude sessions on a medium-sized codebase:

```
┌─────────────────────────────────────────────────────────────────┐
│  Token Usage: Graphify vs Raw Approach                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Without Graphify (raw grep + file reads)                       │
│  ██████████████████████████████████████████████████  ~400k tk   │
│                                                                 │
│  With Graphify (scoped subgraph queries)                        │
│  █                                                  ~1.4k tk   │
│                                                                 │
│  Savings: ~99%                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Per-Query Breakdown

| Approach | Avg tokens/query | What Claude does |
|----------|-----------------|------------------|
| **Raw** | ~8,000 | grep → list files → read each file → summarize |
| **Graphify** | ~18 | `graphify query` → scoped subgraph → answer |

### When Graphify Wins

| Query type | Graphify tokens | Raw tokens | Savings |
|-----------|----------------|------------|---------|
| Architecture overview | ~200 | ~15,000 | 98% |
| Feature module structure | ~150 | ~12,000 | 99% |
| Cross-file relationships | ~300 | ~40,000 | 99% |
| Concept deep-dive | ~250 | ~20,000 | 99% |

### When to Skip Graphify

For narrow lookups (<5 matching files), raw grep is faster:
- Specific function name, config key, or single-file debug
- Graphify overhead (~100ms) exceeds grep savings on tiny scopes

**Rule of thumb:** If a topic spans >5 files, use graphify. Otherwise, grep directly.

### Key Takeaway

```
Graphify: 18 tokens/call  ×  100 calls  =   1,800 tokens
Raw:      8,000 tokens/call ×  100 calls  = 800,000 tokens
                                            ─────────────
                                            798,200 saved (99.8%)
```

This matters most when context window is limited (200k tokens). Graphify keeps room for actual reasoning instead of burning context on raw source dumps.

---

## 🔄 How to Update

To fetch the latest agents, skills, and rules from this repo and sync them to your local CLIs, run:

```bash
cd ~/ai-coding-config
git pull
./install.py
```

---

## 📋 Requirements

- **Node.js**: v18+ (needed for Playwright MCP server execution and TOML merging)
- **Claude Code**: [Install Guide](https://docs.anthropic.com/en/docs/claude-code)
- **Codex CLI**: [Install Guide](https://developers.openai.com/codex)
