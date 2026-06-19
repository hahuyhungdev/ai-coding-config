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
*Tip: This automatically installs the global `ai-config` CLI wrapper in `~/.local/bin/` (make sure this is in your `PATH`). You can re-run `ai-config` at any time to refresh configurations. Add the `--force` flag to run completely non-interactively and auto-overwrite any file conflicts (e.g. `./install.py --force`).*

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
    ai-config init ai
    ```
    Performs deep semantic indexing. By default, this runs in **zero-API-key mode** using your **Antigravity CLI (Gemini) quota** (`gemini-cli` backend).

#### 🚀 Optimization Tips (Speed Boost for AI Mode)
To run AI semantic extraction up to **10x faster**, you can enable parallel execution, increase token budget, or use a faster model:
```bash
# Enable parallel processing & set model to Gemini 3.5 Flash (Low)
export GRAPHIFY_GEMINI_CLI_PARALLEL=1
export GRAPHIFY_GEMINI_CLI_MODEL="Gemini 3.5 Flash (Low)"

# Run extraction with 4 workers and a larger chunk budget
ai-config init ai --max-concurrency 4 --token-budget 120000
```

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
    *Tip: Add the `--force` flag to force a complete, clean rebuild of the graph database from scratch (e.g., `graphify update . --force`).*
*   **Query Codebase Architecture/Context**:
    *   *Architecture Overview:* `rtk graphify query "How does the auth module work?"`
    *   *Code Relationships:* `rtk graphify path "src/main.py" "src/auth.py"`
    *   *Concept Explanation:* `rtk graphify explain "Louvain Clustering"`
    *   *Impact Analysis:* `rtk graphify affected "db_connect"`

### 🛡️ Hook Enforcement & Quota Policies
To protect API tokens and keep context windows compact, the configuration engine installs a unified pre-tool execution hook (`claude/hooks/graphify_pre_tool.py`) for all AI assistants. This hook enforces the following security and exploration rules:
*   **Graphify-First Exploration**: Blocks broad exploration commands (e.g. `ls`, `find`, `grep`, inline Python/Node file reads) and forces the assistant to use Graphify queries first.
*   **Path Leak Protection**: Intercepts edits or file writes containing absolute home directory paths (e.g. `/home/username/...`) and prompts the assistant to use relative paths instead.
*   **Session Graphify Quota**: Restricts the maximum number of Graphify discovery calls to **10 calls per conversation session** to prevent token bloat while allowing sufficient follow-ups during long sessions.

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
*   **[`install.py`](./install.py)**: The main installer entry point. It sets up the entire configuration engine system-wide (Claude Code, Codex CLI, Antigravity CLI, Copilot) and configures MCP servers and token-saving hooks. You can run it with the `--force` flag to auto-overwrite target file conflicts and skip interactive prompts.
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

## 🧠 Skills Catalog

Reusable instruction modules loaded on-demand by AI assistants. Located in [`skills/`](./skills). Each skill has a `SKILL.md` with frontmatter, trigger conditions, and workflow instructions.

### Workflow & Orchestration
| Skill | Description |
| :--- | :--- |
| [`context-budget`](./skills/context-budget) | Audit token overhead across skills/agents/MCPs. Use before adding new components. *(adapted from ECC)* |
| [`council`](./skills/council) | Four-voice structured deliberation (Architect/Skeptic/Pragmatist/Critic) for ambiguous decisions. *(adapted from ECC)* |
| [`compact`](./skills/compact) | Context compaction procedure and strategic guidelines for logical session rollover. |
| [`eval-harness`](./skills/eval-harness) | Formal eval-driven development (EDD) framework with pass@k metrics. |
| [`verification-loop`](./skills/verification-loop) | Post-implementation verification checks. |
| [`tdd-workflow`](./skills/tdd-workflow) | Test-driven development: RED → GREEN → REFACTOR. |

### Code Quality & Review
| Skill | Description |
| :--- | :--- |
| [`coding-standards`](./skills/coding-standards) | Cross-project naming, readability, and immutability conventions. |
| [`karpathy-guidelines`](./skills/karpathy-guidelines) | Behavioral rules to reduce LLM coding mistakes. |
| [`security-review`](./skills/security-review) | Security checklist for auth, APIs, user input, and sensitive features. |
| [`click-path-audit`](./skills/click-path-audit) | Trace handler→state side effects to find silent undos in shared state. *(adapted from ECC)* |
| [`architecture-decision-records`](./skills/architecture-decision-records) | Capture architectural decisions as `docs/adr/` files during sessions. *(adapted from ECC)* |

### Frontend & Design
| Skill | Description |
| :--- | :--- |
| [`frontend-design`](./skills/frontend-design) | Premium interface design avoiding AI slop aesthetics. |
| [`frontend-guide`](./skills/frontend-guide) | Unified guidelines for React component composition, state management, React 19 APIs, and performance optimization. |
| [`design-system`](./skills/design-system) | Design system audit: visual consistency, tokens, and typography. |
| [`next-best-practices`](./skills/next-best-practices) | Next.js App Router conventions, RSC boundaries, data patterns. |
| [`nextjs-turbopack`](./skills/nextjs-turbopack) | Next.js 16+ and Turbopack incremental bundling. |

### Backend & API
| Skill | Description |
| :--- | :--- |
| [`api-design`](./skills/api-design) | REST API design: resource naming, status codes, pagination, versioning. |
| [`backend-patterns`](./skills/backend-patterns) | Backend architecture for Node.js, Express, and Next.js API routes. |
| [`mcp-server-patterns`](./skills/mcp-server-patterns) | Build MCP servers with Node/TypeScript SDK. |

### Codebase & Documentation
| Skill | Description |
| :--- | :--- |
| [`codebase-onboarding`](./skills/codebase-onboarding) | Analyze an unfamiliar codebase and generate a structured onboarding guide. |
| [`graphify`](./skills/graphify) | Any input → knowledge graph → clustered communities → HTML + audit report. |
| [`documentation-lookup`](./skills/documentation-lookup) | Live library/framework docs via Context7 MCP. |
| [`product-lens`](./skills/product-lens) | Validate the "why" before building; pressure-test product direction. |

### Tooling & Automation
| Skill | Description |
| :--- | :--- |
| [`playwright`](./skills/playwright) | E2E testing, visual QA, and Page Object Models via Playwright MCP. |
| [`gh-fix-ci`](./skills/gh-fix-ci) | Debug and fix failing GitHub Actions checks. |
| [`cli-creator`](./skills/cli-creator) | Build composable CLIs exposing stable JSON commands. |

> **Adding new skills:** Run `python3 -m pytest tests/test_skills_integrity.py` after adding any skill to verify frontmatter, structure, and size constraints.

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
