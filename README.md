# 🚀 AI Coding Config

A unified, centralized configuration hub for **Claude Code**, **Codex CLI**, and **Antigravity CLI (agy)**. Manage custom agents, skills, rules (ECC standards), MCP servers, and hooks in one repository and sync them seamlessly across your systems.

---

## ✨ Features

*   **Multi-CLI Support**: Centralized configs for Claude Code, Codex CLI, and Antigravity CLI (`agy`).
*   **Zero-Admin Windows Installation**: Uses Windows Directory Junctions (`mklink /j`) to install files natively without requiring Administrator privileges or Developer Mode.
*   **Auto-Merge TOML Configurations**: Updates Codex's `config.toml` safely by merging new MCP servers and custom agents from the repo while leaving your personal trusted projects (`[projects]`) and settings completely intact.
*   **Browser Lock Protection**: Configures Playwright MCP with `--isolated` automatically for all CLIs to avoid browser profile conflicts.

---

## ⚡ Quick Start

Clone this repository and run the installer to link configuration files to their active CLI locations.

### 🐧 Linux & macOS (Git Bash/WSL)
```bash
git clone git@github.com:hahuyhungdev/ai-coding-config.git ~/ai-coding-config
cd ~/ai-coding-config
./install.sh
```

### 🪟 Windows (CMD / PowerShell)
Run the wrapper batch script (requires Git Bash to be installed in your PATH):
```cmd
git clone git@github.com:hahuyhungdev/ai-coding-config.git %USERPROFILE%\ai-coding-config
cd %USERPROFILE%\ai-coding-config
install.bat
```

---

## ⚙️ Installation Options

You can install configuration assets for all three CLIs at once, or target specific tools selectively using command-line flags.

| Flag | Action |
|---|---|
| `./install.sh --all` | Install configurations for **all** three CLIs (default if no flag is provided) |
| `./install.sh --claude` | Configure **Claude Code** only (`~/.claude/` assets and `~/.claude.json`) |
| `./install.sh --codex` | Configure **Codex CLI** only (`~/.codex/` assets and merging `config.toml`) |
| `./install.sh --agy` | Configure **Antigravity CLI** only (`~/.gemini/config/` assets) |
| `./install.sh -h` | Display the helper menu |

---

## 📂 What's Included

| Component | Claude Code | Codex CLI | Antigravity CLI (`agy`) |
| :--- | :---: | :---: | :---: |
| **Context File** | `CLAUDE.md` | `AGENTS.md` | `ANTIGRAVITY.md` |
| **System Settings** | `settings.json` | `config.toml` | `mcp_config.json` |
| **Custom Agents** | 15 MD agents | 15 TOML agents | 15 MD agents (synced) |
| **Advanced Skills** | 25 skills | 25 skills | 25 skills (synced) |
| **Rules (ECC)** | 12 rules | — | — |
| **Playwright Isolation** | Yes (`--isolated`) | Yes (`--isolated`) | Yes (`--isolated`) |

### 🛠️ Configured MCP Servers
All CLIs are automatically integrated with the following model context protocol servers:
*   `playwright`: Browser automation (running in `--isolated` mode).
*   `context7`: Library documentation lookup (Claude & Gemini only — Codex doesn't support HTTP transport).
*   `memory`: Persistent knowledge graphs.
*   `sequential-thinking`: Step-by-step reasoning support.
*   `github`: Repository management, issues, and PR interactions (Codex only).

Additional MCP servers (`postgres`, `sqlite`, `docker`, `aws`) are available but disabled by default. Use `mcp-toggle` to enable them when needed.

---

## 📁 Repository Structure

```
ai-coding-config/
├── agents/                  # Source of Truth: 15 Custom Agents (.md with YAML frontmatter)
├── skills/                  # Source of Truth: 25 shared skill packages
├── claude/                  # Claude-specific configuration files
│   ├── rules/ecc/           # 12 Engineer Agentic Coding (ECC) rules
│   ├── hooks/               # Pre/Post tool hooks (tracked via .gitkeep)
│   ├── CLAUDE.md            # Claude Code instructions
│   ├── RTK.md               # Claude Code token optimization reference
│   └── settings.json        # Claude settings & Playwright config
├── codex/                   # Codex-specific configuration files
│   ├── AGENTS.md            # Codex instructions
│   ├── RTK.md               # Codex token optimization reference
│   └── config.toml          # Shared Codex config template
├── gemini/                  # Antigravity-specific configuration files
│   └── ANTIGRAVITY.md       # Antigravity instructions
├── scripts/                 # Build & management scripts
│   ├── compile-agents.js    # Compiler script that parses root agents to target folders
│   ├── merge-toml-config.js # Merges Codex config.toml (skips disabled servers)
│   ├── update-mcp-config.js # Updates JSON MCP configs (skips disabled servers)
│   └── mcp-toggle.py        # Toggle MCP servers on/off across all CLIs
├── shared-disabled-mcp.json # Source of truth for disabled MCP servers
├── install.sh               # Main installation Bash script
├── install.bat              # Windows command wrapper
└── README.md
```

---

## 🛠️ How it Works under the Hood

### 🔗 Windows Junctions
Windows symbolic links usually require special Developer Mode permissions. The installer avoids this by using **Directory Junctions** (`mklink /j`) for folders and copying files as a fallback, enabling any standard command prompt or terminal user to install successfully.

### 🔀 Smart TOML Merging
When updating Codex CLI settings, your `~/.codex/config.toml` file is parsed and merged via Node.js:
*   Any newly introduced custom agents or MCP server definitions in this repo are cleanly injected.
*   Your local settings and machine-specific trusted projects (`[projects]`) are fully preserved.

---

## 🔄 How to Update

To fetch the latest agents, skills, and rules from this repo and sync them to your local CLIs, run:

```bash
cd ~/ai-coding-config
git pull
./install.sh
```

---

## 🔀 Managing MCP Servers

Use `mcp-toggle` to enable/disable MCP servers across all three CLIs at once.

```bash
# List all servers
./scripts/mcp-toggle.py list

# Disable a server (keeps config, syncs all CLIs)
./scripts/mcp-toggle.py disable aws

# Enable a server
./scripts/mcp-toggle.py enable postgres

# Bulk operations
./scripts/mcp-toggle.py disable-all
./scripts/mcp-toggle.py enable-all
```

Disabled servers are tracked in `shared-disabled-mcp.json` and respected by `install.sh` — re-running the installer won't re-add them.

---

## 📋 Requirements

*   **Node.js**: v18+ (needed for Playwright MCP server execution and TOML merging)
*   **Claude Code**: [Install Guide](https://docs.anthropic.com/en/docs/claude-code)
*   **Codex CLI**: [Install Guide](https://developers.openai.com/codex)
