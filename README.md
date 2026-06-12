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

### 🧠 Graphify Execution, Clustering, & Rebuild Strategy

To get the highest quality codebase map with the best speed-to-cost ratio, follow this execution and update strategy:

1. **Initial Setup & Big Refactors (Semantic AI Mode):**
   Run the deep semantic extraction to build a high-fidelity knowledge graph (including inferred logical edges and named communities):
   ```bash
   graphify extract . --mode deep --backend gemini
   ```
   *Note: You can choose whichever LLM backend you prefer (`gemini`, `claude-cli`, `openai`, `kimi`, etc.) based on active API keys.*

2. **Louvain Clustering & AI Labeling:**
   Graphify segments codebase modules using **Louvain Community Detection** locally (free & offline).
   *   **Default State:** Communities are named `Community 0`, `Community 1`, etc. in `graphify-out/.graphify_labels.json`.
   *   **AI Community Naming:** Assign descriptive names (e.g. *"Authentication & JWT"*, *"Database Migrations"*) via the LLM:
       ```bash
       graphify label . --backend gemini
       ```
   *   **Re-clustering (After major refactors):** Recalculate community boundaries without losing existing names:
       ```bash
       graphify cluster-only .
       graphify label . --backend gemini
       ```

3. **Daily Commits & Checkouts (Background Git Hooks):**
   Automated background Git Hooks run the offline algorithm-only update:
   ```bash
   graphify update .
   ```
   This updates the graph instantly (1-2 seconds) using local AST and regex parsing. It automatically preserves the named community labels in `graphify-out/.graphify_labels.json` to avoid duplicate LLM calls or burning API limits.

4. **Periodic AI Refresh (Weekly / End of Sprint):**
   To prevent "semantic degradation" (since daily commits only update structural nodes), refresh the semantic edges periodically:
   *   **Linux/WSL (Cron):** Add to `crontab -e`:
       ```bash
       0 22 * * 5 cd ~/projects/ai-coding-config && graphify extract . --mode deep --backend gemini --no-cluster
       ```
   *   **Windows (Command Prompt):** Register a Task Scheduler command:
       ```cmd
       schtasks /create /tn "Graphify AI Refresh" /tr "cmd.exe /c cd C:\projects\ai-coding-config && graphify extract . --mode deep --backend gemini --no-cluster" /sc weekly /d FRI /st 22:00
       ```
   *   *Optimization Tip:* Adding `--no-cluster` skips community grouping, making the rebuild much faster and lighter on tokens.

5. **Quality Auditing (Graph Health Check):**
   Measure the token savings and graph quality at any time:
   ```bash
   graphify benchmark graphify-out/graph.json
   ```

---

## 🔄 Unified Workflow & Configuration Scope

The AI Coding Config Engine manages a three-way sync workflow to align developer tools system-wide.

```
┌──────────────────────────────────────────────────────────┐
│                 Interactive Dashboard                    │
│                 (http://localhost:8000)                  │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼  Saves Enabled Configs
               ┌─────────────┴─────────────┐
               │    server.py Sync Hub     │
               └─┬───────────┬───────────┬─┘
                 │           │           │
                 ▼           ▼           ▼
             [Claude]     [Codex]     [Gemini]
            ~/.claude   ~/.codex   ~/.gemini/config
```

### 1. Workflow
1. **Bootstrap & Project Link:** Run `install.py --all --project /path/to/project`. This injects custom Git Hooks and instructions (`CLAUDE.md`, `ANTIGRAVITY.md`, `AGENTS.md`) into your workspace.
2. **Synchronized Configuration:** Any changes made in the dashboard (enabling/disabling MCP servers, updating custom variables) write concurrently to `~/.claude/settings.json`, `~/.codex/config.toml`, and `~/.gemini/config/mcp_config.json`.
3. **AST-driven Navigation:** When an AI assistant handles a request, Git-based pre-tool-use hooks redirect broad directory/grep searches to `rtk graphify query` to save up to 99.8% of context token budget.
4. **Visual Monitoring:** Open `./run-web.sh` to check active configurations, edit rules inside modals, or visually inspect the module dependency trees, call flows, and 2D network graphs.

### 2. Configuration Scope
*   **Settings File Targets:**
    *   `Claude Code`: JSON structure containing `PreToolUse` hooks and enabled MCP servers.
    *   `Codex CLI`: TOML structure containing `[mcp_servers]` sections and local parameters.
    *   `Antigravity CLI (agy)`: JSON structure containing `BeforeTool` hooks and custom Gemini MCP parameters.
*   **Rules & Markdown instructions:** Sets up and synchronizes project-level rules (like target thresholds, testing requirements) within `CLAUDE.md`, `ANTIGRAVITY.md`, and `AGENTS.md`.
*   **Background Hook Gate:** Automatically registers the `rtk` filter proxy. If the graph exists, it restricts assistants to 3 graph queries maximum per session, forcing context consolidation.

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
| **Advanced Skills** | 26 packages | 26 packages | 26 packages |
| **Rules (ECC)** | 12 rules | — | — |
| **Browser Isolation** | Yes | Yes | Yes |

### 🛠️ Pre-configured MCP Servers
*   `playwright` - Browser automation (running in `--isolated` mode).
*   `context7` - Library documentation lookup.
*   `memory` - Persistent knowledge graphs.
*   `sequential-thinking` - Step-by-step reasoning support.

---

## 🧪 Verification & Test Suite

Verify configurations, security controls, layout alignment, and E2E navigation flows:

### 1. Python Unit Tests (Config & Security)
Runs 68 unit tests verifying template generation, hook execution, and host/CORS security policies:
```bash
pytest
```

### 2. Layout & Structural Alignment Checks
Verifies that all three CLI configuration tabs (Claude, Codex, Gemini) maintain 100% identical settings layout structures:
```bash
node frontend/verify-layout.cjs
```

### 3. Playwright E2E Tests (Full User Flow & Observability)
Verifies tab navigation, adding/removing custom MCP servers, staging changes, log streaming, and analytics detail views:
```bash
# Main E2E flow
node frontend/test-e2e.cjs

# Complex apply scenarios (Standard Apply vs Force Overwrite)
node frontend/test-apply-scenarios.cjs

# Observability dashboard analytics & conversation detail log viewer
node frontend/test-analytics-e2e.cjs
```

---

## 🔒 Security Hardening

The Configuration API server includes built-in protection against cross-site exploitation:
*   **Host Header Validation:** Rejects any requests where the `Host` header is not strictly `localhost` or `127.0.0.1` (protecting against DNS Rebinding and Host Header attacks).
*   **Cross-Origin (CORS) Protection:** Rejects any `POST` requests containing cross-origin `Origin` or `Referer` headers.
*   **Content-Type Enforcement:** Enforces strict `application/json` Content-Type check on all `/api/` endpoints. This forces browsers to perform a CORS preflight OPTIONS check for cross-origin scripts, which is automatically blocked since no wildcard origin headers are allowed.

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
