# 🚀 AI Coding Config Engine

> **Stop burning API tokens. Squeeze them by 99.8% with Graphify & RTK!**
> A unified, centralized configuration hub and interactive control center for **Claude Code**, **Codex CLI**, and **Antigravity CLI (agy)**. Manage custom agents, reusable skills, rules (ECC standards), MCP servers, and environment settings in a single repository and synchronize them across your local system.

---

## ⚡ Quick Start

Clone this repository and link your configurations globally once:

```bash
git clone git@github.com:hahuyhungdev/ai-coding-config.git ~/projects/ai-coding-config
cd ~/projects/ai-coding-config
./install.py
```
Run `./install.py` again whenever you want to refresh the shared configuration.

### 🎯 Initialize a New Project in 1-Second
Navigate to any new project directory and run:
```bash
~/projects/ai-coding-config/install.py --all --project "$PWD"
```
*   **Auto-Scan & Select:** It automatically scans your system for installed AI assistants (`claude`, `agy`, `codex`) and prompts you which ones to configure.
*   **Zero-Token Rebuilds:** It initializes the Graphify graph (`graphify-out/graph.json`) and sets up Git commit/checkout hooks so it updates itself automatically in the background.

---

## 📊 The RTK + Graphify Token Weapon

### 💸 The Problem: Naive Context Burning
Without Graphify, your AI assistant answers codebase questions by running naive `grep` commands, dumping files into the context window, and burning **400,000+ output tokens** in a single session. That is API bankruptcy.

### 🛡️ The Solution: Scoped Subgraphs
By combining `rtk` (our ultra-compact filter proxy) and `graphify` (semantic graph query), we redirect raw grep and read requests to highly optimized scoped subgraphs.

```
┌─────────────────────────────────────────────────────────────────┐
│  Token Usage: Graphify vs Raw Approach                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Without Graphify (raw grep + file dumps)                       │
│  ██████████████████████████████████████████████████  ~400k tk   │
│                                                                 │
│  With Graphify (scoped subgraph queries)                        │
│  █                                                  ~1.4k tk   │
│                                                                 │
│  Savings: ~99.8% of your wallet!                                │
└─────────────────────────────────────────────────────────────────┘
```

### 📈 Metrics at a Glance

| Query Type | Raw Tokens | Graphify Tokens | Wallet Savings |
| :--- | :--- | :--- | :--- |
| **Architecture Overview** | ~15,000 | ~200 | **98.6%** |
| **Feature Module Structure** | ~12,000 | ~150 | **98.7%** |
| **Cross-File Relationships** | ~40,000 | ~300 | **99.2%** |
| **Concept Deep-Dive** | ~20,000 | ~250 | **98.7%** |

### 🧠 Graphify Execution & Rebuild Strategy

To get the highest quality codebase map with the best speed-to-cost ratio, follow this two-tier strategy:

1. **Initial Setup & Big Refactors (Semantic AI Mode):**
   Run the deep semantic extraction using your Claude Code subscription to build a high-fidelity knowledge graph (including inferred logical edges and named communities) completely for free:
   ```bash
   graphify extract . --mode deep --backend claude-cli
   ```
   *Note: Ensure you are logged into the `claude` CLI (`claude` command works) beforehand.*

2. **Daily Commits & Checkouts (Background Git Hooks):**
   Let the automated background Git Hooks run the offline algorithm-only update:
   ```bash
   graphify update .
   ```
   This updates the graph instantly (1-2 seconds) using local AST and regex parsing for modified/new/deleted files without blocking your terminal or burning API limits.

---

## 🖥️ Interactive Web Dashboard

Manage your agents, configurations, and MCP servers visually.

```bash
./run-web.sh
# or python3 server.py --port 8000
```

*   **Interactive Toggles:** Toggle active CLI targets and individual MCP servers in real-time.
*   **Visual Diffs:** Inspect staged changes in a sidebar before writing to disk.
*   **Modal Editors:** Access and edit `CLAUDE.md`, `AGENTS.md`, and `ANTIGRAVITY.md` on-demand inside popup modal dialogs, leaving configuration pages clean.

---

## ⚙️ What's Inside

| Feature / CLI | Claude Code | Codex CLI | Antigravity CLI (`agy`) |
| :--- | :---: | :---: | :---: |
| **Global Path** | `~/.claude` | `~/.codex` | `~/.gemini/config` |
| **Config File** | `settings.json` | `config.toml` | `settings.json` |
| **Custom Agents** | 15 MD agents | 15 TOML agents | 15 MD agents |
| **Advanced Skills** | 25 packages | 25 packages | 25 packages |
| **Rules (ECC)** | 12 rules | — | — |
| **Browser Isolation** | Yes | Yes | Yes |

### 🛠️ Pre-configured MCP Servers
*   `playwright` - Browser automation (running in `--isolated` mode).
*   `context7` - Library documentation lookup.
*   `memory` - Persistent knowledge graphs.
*   `sequential-thinking` - Step-by-step reasoning support.

---

## 🧪 Verification & Test Suite

Verify syntax, templates, and hook-filtering behavior locally:

```bash
python3 -m unittest tests/test_config.py
python3 -m unittest tests/test_cal_diy_integration.py
```

---

## 🔄 How to Update

To fetch the latest agents, skills, and rules from this repo and sync them to your local CLIs, run:

```bash
git pull && ./install.py
```

---

## 📋 Requirements

- **Node.js**: v18+ (needed for Playwright MCP server execution and TOML merging)
- **Claude Code**: [Install Guide](https://docs.anthropic.com/en/docs/claude-code)
- **Codex CLI**: [Install Guide](https://developers.openai.com/codex)
