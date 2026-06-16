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

### 🚀 Standalone Antigravity CLI (agy) Setup
If you only want to install the `agy` quota status checker wrapper and manage Gemini accounts without setting up the entire config engine:
```bash
python3 install-agy.py
```
*   **Ubuntu / Linux:** Add `export PATH="$HOME/.local/bin:$PATH"` to your `~/.bashrc` or `~/.zshrc` if not already present, then run `source ~/.bashrc`.
*   **Windows:** Make sure your Windows `PATH` environment variable includes `%USERPROFILE%\.local\bin`.
*   **Verify Globally:** Run `agy status` from any directory.
*   **Manage Accounts:** Run `agy account list`, `agy account add`, and `agy account use <target>`.
*   **Full CLI Guide:** See [`docs/AGY_CLI.md`](docs/AGY_CLI.md).

### 2. Initialize a Project in 1-Second
Navigate to any project directory and run:

*   **Offline AST Mode (Default):**
    ```bash
    ai-config init
    ```
    Links active AI assistants (`claude`, `agy`, `codex`), sets up project guidelines (`CLAUDE.md`, etc.), and configures background git hooks for offline AST updates.

*   **AI Semantic Mode (Deep Extraction):**
    ```bash
    ai-config init-ai [--backend <gemini|openai|claude>]
    ```
    Performs deep semantic indexing using LLM API keys. It automatically scans active environment variables or prompts for temporary input if keys are not set.

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

## 📂 Repository File Structure & Installation Scripts

The repository contains several scripts and directories with similar names (e.g., related to `install` or `graphify`). Here is a quick reference to clarify their specific roles:

### ⚙️ Installation & Setup Scripts
*   **[`install.py`](./install.py)**: The main installer entry point. It sets up the entire configuration engine system-wide (Claude Code, Codex CLI, Antigravity CLI, Copilot) and configures MCP servers and token-saving hooks.
*   **[`install.bat`](./install.bat)**: A simple Windows batch file wrapper that runs `install.py`.
*   **[`install-agy.py`](./install-agy.py)**: A standalone, lightweight installer. Use this if you *only* want to install the Antigravity CLI status checker (`agy`) and manage Gemini accounts without installing the full config suite.
*   **[`installer/`](./installer)**: A Python package containing helper modules used by `install.py`:
    *   `setup.py`: Core installation and configuration logic for individual assistants.
    *   `file_ops.py`: File actions (copying templates, backups, JSON/TOML merging).
    *   `mcp.py` / `agents.py`: MCP server and agent configuration handlers.
    *   `cli.py`: Terminal UI printing and logging helpers.

### 🕸️ Graphify Assets (Knowledge Graph Engine)
*   **[`installer_graphify.py`](./installer_graphify.py)**: Manages the configuration and injection of Graphify's pre-tool hooks into the AI assistant configurations. It is called by the main installer during setup.
*   **[`skills/graphify/`](./skills/graphify)**: The skill bundle containing instructions and guides (`SKILL.md`) that teach the AI how to use Graphify commands during a coding session.
*   **[`plugins/graphify/`](./plugins/graphify)**: The system-level plugin configuration folder.
*   **`graphify-out/`**: A generated directory containing local repository subgraphs and index metadata (created after running `graphify update .`).

---

## 🧪 Verification & Testing

Verify system behavior, security headers, and user flows:
*   **Run Unit Tests**: `pytest`
*   **Run E2E UI Tests**: `node frontend/test-e2e.cjs`
*   **Verify Assistant Layout Consistency**: `node frontend/verify-layout.cjs`

---

## 🗑️ Uninstallation

If you need to remove the configurations and wrapper scripts:

*   **Uninstall global AI Coding Config engine** (Claude/Codex assets & global `ai-config` wrapper):
    ```bash
    ./install.py --uninstall
    ```

*   **Uninstall standalone Antigravity CLI (agy)**:
    ```bash
    python3 install-agy.py --uninstall
    ```
