#!/usr/bin/env bash
set -euo pipefail

# AI Coding Config Installer
# Symlinks Claude Code and Codex CLI configs from this repo to their expected locations.

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
CODEX_DIR="$HOME/.codex"

info() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
ok()   { echo -e "\033[0;32m[OK]\033[0m $1"; }
warn() { echo -e "\033[0;33m[WARN]\033[0m $1"; }

# --- Claude Code ---
info "Setting up Claude Code..."

mkdir -p "$CLAUDE_DIR"/{agents,skills,rules/ecc,rules/common,hooks}

# CLAUDE.md
ln -sf "$REPO_DIR/claude/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"
ok "CLAUDE.md"

# settings.json
if [ -f "$CLAUDE_DIR/settings.json" ]; then
    warn "settings.json exists — backing up to settings.json.bak"
    cp "$CLAUDE_DIR/settings.json" "$CLAUDE_DIR/settings.json.bak"
fi
ln -sf "$REPO_DIR/claude/settings.json" "$CLAUDE_DIR/settings.json"
ok "settings.json"

# RTK.md
ln -sf "$REPO_DIR/claude/RTK.md" "$CLAUDE_DIR/RTK.md"
ok "RTK.md"

# Agents
for f in "$REPO_DIR"/claude/agents/*.md; do
    name="$(basename "$f")"
    ln -sf "$f" "$CLAUDE_DIR/agents/$name"
done
ok "Agents ($(ls "$REPO_DIR"/claude/agents/*.md | wc -l) files)"

# Skills
for d in "$REPO_DIR"/claude/skills/*/; do
    name="$(basename "$d")"
    ln -sf "$d" "$CLAUDE_DIR/skills/$name"
done
ok "Skills ($(ls -d "$REPO_DIR"/claude/skills/*/ | wc -l) dirs)"

# Rules
for f in "$REPO_DIR"/claude/rules/ecc/*.md; do
    name="$(basename "$f")"
    ln -sf "$f" "$CLAUDE_DIR/rules/ecc/$name"
done
for f in "$REPO_DIR"/claude/rules/common/*.md; do
    name="$(basename "$f")"
    ln -sf "$f" "$CLAUDE_DIR/rules/common/$name"
done
ok "Rules"

# Hooks
if [ -d "$REPO_DIR/claude/hooks" ] && [ "$(ls -A "$REPO_DIR/claude/hooks" 2>/dev/null)" ]; then
    for f in "$REPO_DIR"/claude/hooks/*; do
        name="$(basename "$f")"
        ln -sf "$f" "$CLAUDE_DIR/hooks/$name"
    done
    ok "Hooks"
else
    warn "No hooks to install"
fi

# --- Codex CLI ---
info "Setting up Codex CLI..."

mkdir -p "$CODEX_DIR"/{agents,skills}

# AGENTS.md
ln -sf "$REPO_DIR/codex/AGENTS.md" "$CODEX_DIR/AGENTS.md"
ok "AGENTS.md"

# RTK.md
ln -sf "$REPO_DIR/codex/RTK.md" "$CODEX_DIR/RTK.md"
ok "RTK.md"

# config.toml
if [ -f "$CODEX_DIR/config.toml" ]; then
    warn "config.toml exists — backing up to config.toml.bak"
    cp "$CODEX_DIR/config.toml" "$CODEX_DIR/config.toml.bak"
fi
ln -sf "$REPO_DIR/codex/config.toml" "$CODEX_DIR/config.toml"
ok "config.toml"

# Agents
for f in "$REPO_DIR"/codex/agents/*.toml; do
    name="$(basename "$f")"
    ln -sf "$f" "$CODEX_DIR/agents/$name"
done
ok "Agents ($(ls "$REPO_DIR"/codex/agents/*.toml | wc -l) files)"

# Skills
for d in "$REPO_DIR"/codex/skills/*/; do
    name="$(basename "$d")"
    ln -sf "$d" "$CODEX_DIR/skills/$name"
done
ok "Skills ($(ls -d "$REPO_DIR"/codex/skills/*/ | wc -l) dirs)"

echo ""
echo "Done! Restart Claude Code / Codex CLI to pick up changes."
echo ""
echo "NOTE: Add your project trust paths to codex/config.toml:"
echo '  [projects."/path/to/project"]'
echo '  trust_level = "trusted"'
