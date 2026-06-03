# AI Coding Config

Unified configuration for **Claude Code** and **Codex CLI** — agents, skills, rules, MCP servers, and hooks in one repo.

## What's Included

| Component | Claude Code | Codex CLI |
|-----------|------------|-----------|
| Context file | `CLAUDE.md` | `AGENTS.md` |
| Settings | `settings.json` | `config.toml` |
| Agents | 12 (`.md`) | 15 (`.toml`) |
| Skills | 25 | 25 |
| Rules | 12 ECC + common | — |
| MCP servers | 5 (via ECC) | 5 (config.toml) |
| RTK reference | ✅ | ✅ |

## Quick Start

```bash
git clone git@github.com:hahuyhungdev/ai-coding-config.git ~/ai-coding-config
cd ~/ai-coding-config
chmod +x install.sh
./install.sh
```

The installer creates symlinks from this repo to `~/.claude/` and `~/.codex/`. Your existing configs are backed up before overwriting.

## Structure

```
ai-coding-config/
├── claude/
│   ├── CLAUDE.md           # Global instructions
│   ├── settings.json       # Permissions, env vars
│   ├── RTK.md              # Token optimization reference
│   ├── agents/             # 12 agent definitions (.md)
│   ├── skills/             # 25 skills (SKILL.md each)
│   ├── rules/
│   │   ├── ecc/            # 12 ECC rule files
│   │   └── common/         # Shared rules (coding-style, security, etc.)
│   └── hooks/              # Pre/Post tool hooks (add your own)
├── codex/
│   ├── AGENTS.md           # Codex instructions
│   ├── config.toml         # MCP servers, agents, profiles
│   ├── RTK.md              # Token optimization reference
│   ├── agents/             # 15 agent definitions (.toml)
│   └── skills/             # 25 skills (SKILL.md each)
├── install.sh              # Symlink installer
└── README.md
```

## Agents

### Claude Code (12)

| Agent | Purpose |
|-------|---------|
| planner | Implementation planning |
| code-reviewer | Code quality review |
| security-reviewer | Security analysis |
| build-error-resolver | Fix build/type errors |
| tdd-guide | Test-driven development |
| typescript-reviewer | TypeScript/JS review |
| database-reviewer | PostgreSQL specialist |
| e2e-runner | Playwright E2E testing |
| performance-optimizer | Performance analysis |
| refactor-cleaner | Dead code cleanup |
| code-explorer | Codebase analysis |
| architect | System design |

### Codex CLI (15)

All 12 above, plus:

| Agent | Purpose |
|-------|---------|
| explorer | Read-only codebase exploration |
| reviewer | PR review (correctness + security) |
| docs-researcher | API/docs verification |

## Skills (25)

`api-design` · `backend-patterns` · `browser-qa` · `cli-creator` · `codebase-onboarding` · `coding-standards` · `composition-patterns` · `design-system` · `documentation-lookup` · `e2e-testing` · `eval-harness` · `frontend-design` · `frontend-patterns` · `gh-fix-ci` · `karpathy-guidelines` · `mcp-server-patterns` · `next-best-practices` · `nextjs-turbopack` · `playwright` · `product-lens` · `security-best-practices` · `security-review` · `strategic-compact` · `tdd-workflow` · `verification-loop`

## MCP Servers

| Server | Purpose |
|--------|---------|
| github | GitHub API (issues, PRs, repos) |
| context7 | Library documentation lookup |
| playwright | Browser automation |
| memory | Persistent knowledge graph |
| sequential-thinking | Step-by-step reasoning |

## Customization

### Add a project to Codex trust list

Edit `codex/config.toml`:

```toml
[projects."/path/to/your/project"]
trust_level = "trusted"
```

### Add custom hooks

Create files in `claude/hooks/` and reference them in your hooks config.

### Add new skills

Create a directory under `claude/skills/` or `codex/skills/` with a `SKILL.md` file.

## Updating

```bash
cd ~/ai-coding-config
git pull
./install.sh  # Re-symlinks (idempotent)
```

## Requirements

- **Claude Code**: [Install guide](https://docs.anthropic.com/en/docs/claude-code)
- **Codex CLI**: [Install guide](https://developers.openai.com/codex)
- **Node.js**: 18+ (for MCP servers)
- **RTK** (optional): `curl -sSL https://rtk.apidocumentation.com/install.sh | bash`
