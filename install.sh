#!/usr/bin/env bash
set -euo pipefail

# AI Coding Config Installer
# Links shared Claude/Codex assets from this repo to their expected locations.
# Codex config.toml is copied, not linked, so each machine can keep local trusted projects.

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
CODEX_DIR="$HOME/.codex"
RTK_INSTALL_URL="https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh"

info() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
ok()   { echo -e "\033[0;32m[OK]\033[0m $1"; }
warn() { echo -e "\033[0;33m[WARN]\033[0m $1"; }

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

is_windows() {
    case "$(uname -s)" in
        *MSYS*|*MINGW*|*CYGWIN*) return 0 ;;
        *) return 1 ;;
    esac
}

link_path() {
    local source="$1"
    local target="$2"
    local backup

    if [ ! -e "$source" ] && [ ! -L "$source" ]; then
        warn "Source does not exist: $source"
        return 1
    fi

    if [ -e "$target" ] || [ -L "$target" ]; then
        if [ -L "$target" ] || (is_windows && [ -d "$target" ]); then
            rm -rf "$target"
        else
            backup="$target.bak.$(date +%Y%m%d%H%M%S)"
            warn "$(basename "$target") exists - moving to $(basename "$backup")"
            mv "$target" "$backup"
        fi
    fi

    if is_windows; then
        local win_source
        local win_target
        win_source=$(cygpath -w "$source")
        win_target=$(cygpath -w "$target")
        local is_dir=""
        if [ -d "$source" ]; then
            is_dir="/d"
        fi
        if ! cmd.exe /c mklink $is_dir "$win_target" "$win_source" >/dev/null 2>&1; then
            warn "Failed to create symlink, copying instead: $target"
            cp -R "$source" "$target"
        fi
    else
        ln -s "$source" "$target"
    fi
}

install_local_config() {
    local source="$1"
    local target="$2"

    if [ -L "$target" ]; then
        warn "$(basename "$target") is linked - replacing with a local config copy"
        rm "$target"
        cp "$source" "$target"
        return
    fi

    if [ -e "$target" ]; then
        warn "$(basename "$target") exists - keeping local config unchanged"
        return
    fi

    cp "$source" "$target"
}

install_rtk_binary() {
    local temp_dir
    local install_script

    if ! command_exists curl; then
        warn "curl is not installed - skipping RTK install"
        return 1
    fi

    temp_dir="$(mktemp -d)"
    install_script="$temp_dir/install-rtk.sh"

    curl -fsSL "$RTK_INSTALL_URL" -o "$install_script"
    bash "$install_script"

    export PATH="$HOME/.local/bin:$PATH"
}

configure_rtk() {
    local answer
    local version

    if ! command_exists rtk; then
        if [ "${RTK_INSTALL:-0}" = "1" ]; then
            install_rtk_binary || return
        elif [ -t 0 ]; then
            echo ""
            read -r -p "RTK is not installed. Install it now? [Y/n] " answer
            case "$answer" in
                n|N|no|NO|No)
                    warn "Skipping RTK install"
                    return
                    ;;
                *)
                    install_rtk_binary || return
                    ;;
            esac
        else
            warn "RTK is not installed - set RTK_INSTALL=1 to install non-interactively"
            return
        fi
    fi

    if command_exists rtk; then
        rtk config --create >/dev/null 2>&1 || true
        version="$(rtk --version 2>/dev/null || true)"
        ok "RTK ready${version:+ ($version)}"
    fi
}

expand_trust_path() {
    local path="$1"

    case "$path" in
        "~") printf '%s\n' "$HOME" ;;
        "~/"*) printf '%s/%s\n' "$HOME" "${path#~/}" ;;
        '$HOME') printf '%s\n' "$HOME" ;;
        '$HOME/'*) printf '%s/%s\n' "$HOME" "${path#\$HOME/}" ;;
        *) printf '%s\n' "$path" ;;
    esac
}

detect_username() {
    id -un 2>/dev/null || printf '%s\n' "${USER:-user}"
}

append_csv_trusted_projects() {
    local config="$1"
    local paths="$2"
    local path

    IFS=',' read -r -a TRUST_PATHS <<< "$paths"
    for path in "${TRUST_PATHS[@]}"; do
        path="${path#"${path%%[![:space:]]*}"}"
        path="${path%"${path##*[![:space:]]}"}"
        add_trusted_project "$config" "$path"
    done
}

trusted_project_count() {
    local config="$1"

    sed -n 's/^\[projects\."\([^"]*\)"\]$/\1/p' "$config" | wc -l | awk '{print $1}'
}

trusted_project_exists() {
    local config="$1"
    local project_path="$2"
    local trusted_path

    while IFS= read -r trusted_path; do
        if [ "$project_path" = "$trusted_path" ]; then
            ok "Trusted project already present: $project_path"
            return 0
        fi
    done < <(sed -n 's/^\[projects\."\([^"]*\)"\]$/\1/p' "$config")

    return 1
}

add_trusted_project() {
    local config="$1"
    local raw_path="$2"
    local project_path

    project_path="$(expand_trust_path "$raw_path")"

    if [ -z "$project_path" ]; then
        return
    fi

    if printf '%s' "$project_path" | grep -q '["\\]'; then
        warn "Skipping path with unsupported quote/backslash character: $project_path"
        return
    fi

    if trusted_project_exists "$config" "$project_path"; then
        return
    fi

    {
        echo ""
        echo "[projects.\"$project_path\"]"
        echo 'trust_level = "trusted"'
    } >> "$config"

    ok "Trusted project added: $project_path"
}

configure_codex_trusted_projects() {
    local config="$1"
    local username
    local detected_username
    local default_home
    local local_home
    local default_paths
    local paths

    if [ -n "${CODEX_TRUSTED_PROJECTS:-}" ]; then
        append_csv_trusted_projects "$config" "$CODEX_TRUSTED_PROJECTS"
        return
    fi

    if [ "${CODEX_RECONFIGURE_TRUST:-0}" != "1" ] && [ "$(trusted_project_count "$config")" -gt 0 ]; then
        ok "Codex trusted projects already configured"
        return
    fi

    if [ ! -t 0 ]; then
        warn "Non-interactive shell - skipping Codex trusted project setup"
        return
    fi

    echo ""
    info "Configuring local Codex trusted projects..."

    detected_username="${CODEX_LOCAL_USERNAME:-$(detect_username)}"
    read -r -p "OS username [$detected_username]: " username
    username="${username:-$detected_username}"

    default_home="${CODEX_LOCAL_HOME:-$HOME}"
    if [ -z "$default_home" ] || [ "$default_home" = "/" ]; then
        default_home="/home/$username"
    fi

    read -r -p "Home directory [$default_home]: " local_home
    local_home="${local_home:-$default_home}"

    default_paths="$local_home/projects,$local_home/projects/personals,$local_home/projects/company,$REPO_DIR"

    echo "Trusted project roots are comma-separated. Press Enter to accept defaults."
    echo "Defaults: $default_paths"
    read -r -p "Trusted project roots: " paths
    paths="${paths:-$default_paths}"

    append_csv_trusted_projects "$config" "$paths"
}

update_json_mcp_config() {
    local file="$1"
    if [ -f "$file" ]; then
        node -e '
const fs = require("fs");
const file = process.argv[1];
try {
    const data = JSON.parse(fs.readFileSync(file, "utf8"));
    if (data && data.mcpServers && data.mcpServers.playwright && data.mcpServers.playwright.args) {
        const args = data.mcpServers.playwright.args;
        if (!args.includes("--isolated")) {
            args.push("--isolated");
            fs.writeFileSync(file, JSON.stringify(data, null, 2), "utf8");
            console.log("Added --isolated to " + file);
        }
    }
} catch (e) {
    console.error("Error updating " + file + ":", e.message);
}
' "$file"
    fi
}

# --- Claude Code ---
count_files() {
    local dir="$1"
    local pattern="$2"

    find "$dir" -maxdepth 1 -type f -name "$pattern" | wc -l | awk '{print $1}'
}

count_dirs() {
    local dir="$1"

    find "$dir" -mindepth 1 -maxdepth 1 -type d | wc -l | awk '{print $1}'
}

info "Setting up Claude Code..."

mkdir -p "$CLAUDE_DIR"/{agents,skills,rules/ecc,hooks}

# CLAUDE.md
link_path "$REPO_DIR/claude/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"
ok "CLAUDE.md"

# settings.json
link_path "$REPO_DIR/claude/settings.json" "$CLAUDE_DIR/settings.json"
ok "settings.json"

# RTK.md
link_path "$REPO_DIR/claude/RTK.md" "$CLAUDE_DIR/RTK.md"
ok "RTK.md"

# Agents
for f in "$REPO_DIR"/claude/agents/*.md; do
    name="$(basename "$f")"
    link_path "$f" "$CLAUDE_DIR/agents/$name"
done
ok "Agents ($(count_files "$REPO_DIR/claude/agents" "*.md") files)"

# Skills
for d in "$REPO_DIR"/claude/skills/*/; do
    name="$(basename "$d")"
    link_path "$d" "$CLAUDE_DIR/skills/$name"
done
ok "Skills ($(count_dirs "$REPO_DIR/claude/skills") dirs)"

# Rules (ECC only)
for f in "$REPO_DIR"/claude/rules/ecc/*.md; do
    name="$(basename "$f")"
    link_path "$f" "$CLAUDE_DIR/rules/ecc/$name"
done
ok "Rules ($(count_files "$REPO_DIR/claude/rules/ecc" "*.md") files)"

# Hooks
if [ -d "$REPO_DIR/claude/hooks" ] && [ "$(ls -A "$REPO_DIR/claude/hooks" 2>/dev/null)" ]; then
    for f in "$REPO_DIR"/claude/hooks/*; do
        name="$(basename "$f")"
        link_path "$f" "$CLAUDE_DIR/hooks/$name"
    done
    ok "Hooks"
else
    warn "No hooks to install"
fi

# --- Codex CLI ---
info "Setting up Codex CLI..."

mkdir -p "$CODEX_DIR"/{agents,skills}

# AGENTS.md
link_path "$REPO_DIR/codex/AGENTS.md" "$CODEX_DIR/AGENTS.md"
ok "AGENTS.md"

# RTK.md
link_path "$REPO_DIR/codex/RTK.md" "$CODEX_DIR/RTK.md"
ok "RTK.md"
configure_rtk

# config.toml
install_local_config "$REPO_DIR/codex/config.toml" "$CODEX_DIR/config.toml"
ok "config.toml"
configure_codex_trusted_projects "$CODEX_DIR/config.toml"

# Agents
for f in "$REPO_DIR"/codex/agents/*.toml; do
    name="$(basename "$f")"
    link_path "$f" "$CODEX_DIR/agents/$name"
done
ok "Agents ($(count_files "$REPO_DIR/codex/agents" "*.toml") files)"

# Skills
for d in "$REPO_DIR"/codex/skills/*/; do
    name="$(basename "$d")"
    link_path "$d" "$CODEX_DIR/skills/$name"
done
ok "Skills ($(count_dirs "$REPO_DIR/codex/skills") dirs)"

# --- Antigravity CLI (agy) ---
info "Setting up Antigravity CLI (agy)..."

if [ -L "$HOME/.gemini/config/skills" ]; then
    ok "Skills directory is already symlinked for agy"
else
    mkdir -p "$HOME/.gemini/config/skills"
    for d in "$REPO_DIR"/claude/skills/*/; do
        name="$(basename "$d")"
        link_path "$d" "$HOME/.gemini/config/skills/$name"
    done
    ok "Skills ($(count_dirs "$REPO_DIR/claude/skills") dirs) linked to agy config"
fi

if [ -L "$HOME/.gemini/config/agents" ]; then
    ok "Agents directory is already symlinked for agy"
else
    mkdir -p "$HOME/.gemini/config/agents"
fi

# Update Playwright MCP configurations for all three CLIs (Claude, agy, Codex)
info "Ensuring Playwright MCP runs with --isolated..."
update_json_mcp_config "$HOME/.claude.json"
update_json_mcp_config "$HOME/.gemini/config/mcp_config.json"
update_json_mcp_config "$HOME/.claude/ecc-source/mcp-configs/mcp-servers.json"

echo ""
echo "Done! Restart Claude Code / Codex CLI / agy to pick up changes."
echo ""
echo "NOTE: Re-run ./install.sh any time to refresh shared assets."
echo "      Personal Codex trusted projects stay in ~/.codex/config.toml."
