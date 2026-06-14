# 🚀 AI Coding Config Engine

> **Stop burning API tokens. Squeeze context usage by up to 99.8% using Graphify & RTK!**
> A unified, centralized configuration hub and interactive control center for **Claude Code**, **Codex CLI**, and **Antigravity CLI (agy)**. Manage custom agents, reusable skills, rules (ECC standards), MCP servers, and environment settings in one place.

---

## ⚡ Quick Start

### 1. Global Setup (Run Once)
Clone the repository and link your configurations globally:
```bash
git clone git@github.com:hahuyhungdev/ai-coding-config.git ~/projects/ai-coding-config
cd ~/projects/ai-coding-config
./install.py
```
*Tip: This automatically installs the global `ai-config` CLI wrapper in `~/.local/bin/` (make sure this is in your `PATH`). You can re-run `ai-config` at any time to refresh configurations.*

### 2. Initialize a Project in 1-Second
Navigate to any project directory and run:
```bash
ai-config init
```
This automatically:
*   Scans and links your active AI assistants (`claude`, `agy`, `codex`).
*   Sets up project-level guidelines (`CLAUDE.md`, `ANTIGRAVITY.md`, `AGENTS.md`).
*   Configures background Git hooks to auto-update the Graphify codebase index on commit/checkout.

---

## 🛠️ Practical Usage

### 🖥️ Interactive Web Dashboard
Manage your configuration, toggle active CLI targets, edit rules, or view staged changes in real-time:
```bash
./run-web.sh
# Server runs at http://127.0.0.1:8000
```

### 🧠 Token-Saving (RTK + Graphify)
Instead of dumping full files and burning thousands of tokens, redirect broad queries to highly optimized codebase subgraphs:

*   **Update the Graph** (usually automated by git hooks):
    ```bash
    graphify update .
    ```
*   **Query Codebase Architecture/Context**:
    *   *Architecture Overview:* `rtk graphify query "How does the auth module work?"`
    *   *Code Relationships:* `rtk graphify path "src/main.py" "src/auth.py"`
    *   *Concept Explanation:* `rtk graphify explain "Louvain Clustering"`
    *   *Impact Analysis:* `rtk graphify affected "db_connect"`

### ⚙️ Pre-configured MCP Servers
The engine registers and configures key MCP servers system-wide:
*   `playwright`: Browser automation and E2E visual verification.
*   `context7`: Live library documentation lookup.
*   `memory`: Persistent knowledge graphs.
*   `sequential-thinking`: Step-by-step problem-solving.

---

## ⚙️ Configuration Targets

| CLI Assistant | Target Config File | Global Path |
| :--- | :--- | :--- |
| **Claude Code** | `settings.json` | `~/.claude` |
| **Codex CLI** | `config.toml` | `~/.codex` |
| **Antigravity (`agy`)** | `settings.json` | `~/.gemini/config` |

---

## 🧪 Verification & Testing

Verify system behavior, security headers, and user flows:
*   **Run Unit Tests**: `pytest`
*   **Run E2E UI Tests**: `node frontend/test-e2e.cjs`
*   **Verify Assistant Layout Consistency**: `node frontend/verify-layout.cjs`
