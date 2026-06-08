#!/usr/bin/env bash
set -euo pipefail

# AI Coding Config Installer
# Copies shared Claude/Codex/Gemini assets from this repo to their expected locations.
# Detects conflicts and lets user decide: overwrite, keep, or skip.

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
CODEX_DIR="$HOME/.codex"
RTK_INSTALL_URL="https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh"

info() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
ok() { echo -e "\033[0;32m[OK]\033[0m $1"; }
warn() { echo -e "\033[0;33m[WARN]\033[0m $1"; }

INSTALL_CLAUDE=0
INSTALL_CODEX=0
INSTALL_AGY=0
FORCE=0

# Parse arguments
if [ $# -eq 0 ]; then
    INSTALL_CLAUDE=1
    INSTALL_CODEX=1
    INSTALL_AGY=1
else
    while [ $# -gt 0 ]; do
        case "$1" in
            --claude)
                INSTALL_CLAUDE=1
                shift
                ;;
            --codex)
                INSTALL_CODEX=1
                shift
                ;;
            --agy)
                INSTALL_AGY=1
                shift
                ;;
            --all)
                INSTALL_CLAUDE=1
                INSTALL_CODEX=1
                INSTALL_AGY=1
                shift
                ;;
            --force)
                FORCE=1
                shift
                ;;
            -h | --help)
                echo "Usage: ./install.sh [options]"
                echo "Options:"
                echo "  --claude    Only install/configure Claude Code"
                echo "  --codex     Only install/configure Codex CLI"
                echo "  --agy       Only install/configure Antigravity CLI (agy)"
                echo "  --all       Install/configure all three (default)"
                echo "  --force     Overwrite all without asking"
                echo "  -h, --help  Show this help message"
                exit 0
                ;;
            *)
                warn "Unknown option: $1"
                shift
                ;;
        esac
    done
fi

# Compile shared Markdown agents to CLI-specific formats
info "Compiling custom agents..."
COMPILE_FLAGS=""
if [ "$INSTALL_CLAUDE" = "1" ]; then COMPILE_FLAGS="$COMPILE_FLAGS --claude"; fi
if [ "$INSTALL_CODEX" = "1" ]; then COMPILE_FLAGS="$COMPILE_FLAGS --codex"; fi
if [ "$INSTALL_AGY" = "1" ]; then COMPILE_FLAGS="$COMPILE_FLAGS --agy"; fi
node "$REPO_DIR/scripts/compile-agents.js" $COMPILE_FLAGS

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

is_windows() {
    case "$(uname -s)" in
        *MSYS* | *MINGW* | *CYGWIN*) return 0 ;;
        *) return 1 ;;
    esac
}

copy_config() {
    local source="$1"
    local target="$2"
    local choice

    if [ ! -e "$source" ] && [ ! -L "$source" ]; then
        warn "Source does not exist: $source"
        return 1
    fi

    # Remove old symlink (from previous installs)
    if [ -L "$target" ]; then
        rm -f "$target"
    fi

    # Target doesn't exist → copy directly
    if [ ! -e "$target" ]; then
        cp -R "$source" "$target"
        return 0
    fi

    # Target exists → check for differences
    if [ -d "$source" ] && [ -d "$target" ]; then
        # Directory: compare recursively
        if diff -rq "$source" "$target" >/dev/null 2>&1; then
            return 0  # Same, skip
        fi
    elif [ -f "$source" ] && [ -f "$target" ]; then
        # File: compare content
        if cmp -s "$source" "$target"; then
            return 0  # Same, skip
        fi
    fi

    # Conflict detected
    echo ""
    warn "Conflict detected: $(basename "$target")"
    echo "  Repo:   $source"
    echo "  Global: $target"

    if [ "$FORCE" = "1" ]; then
        cp -R "$source" "$target"
        ok "Overwritten (force): $(basename "$target")"
        return 0
    fi

    if [ -t 0 ]; then
        # Interactive: show diff and ask
        if [ -f "$source" ] && [ -f "$target" ]; then
            echo ""
            diff --color=auto "$source" "$target" | head -30 || true
        elif [ -d "$source" ] && [ -d "$target" ]; then
            echo ""
            diff -rq "$source" "$target" | head -20
        fi
        echo ""
        echo "  [o] Overwrite  [k] Keep current  [s] Skip"
        read -r -p "  Choice: " choice
        case "$choice" in
            o|O)
                cp -R "$source" "$target"
                ok "Overwritten: $(basename "$target")"
                ;;
            k|K)
                ok "Kept current: $(basename "$target")"
                ;;
            *)
                ok "Skipped: $(basename "$target")"
                ;;
        esac
    else
        # Non-interactive: skip with warning
        warn "Skipping conflict (non-interactive): $(basename "$target")"
        warn "Use --force to overwrite all"
    fi
}

install_local_config() {
    local source="$1"
    local target="$2"

    # Remove old symlink (from previous installs)
    if [ -L "$target" ]; then
        warn "$(basename "$target") is symlinked - replacing with copy"
        rm "$target"
        cp "$source" "$target"
        return
    fi

    if [ -f "$target" ]; then
        if cmp -s "$source" "$target"; then
            return 0  # Same, skip
        fi
        info "Merging $source configurations into $target..."
        node "$REPO_DIR/scripts/merge-toml-config.js" "$source" "$target"
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
                n | N | no | NO | No)
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

    IFS=',' read -r -a TRUST_PATHS <<<"$paths"
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
    } >>"$config"

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

count_files() {
    local dir="$1"
    local pattern="$2"

    find "$dir" -maxdepth 1 -type f -name "$pattern" | wc -l | awk '{print $1}'
}

count_dirs() {
    local dir="$1"

    find "$dir" -mindepth 1 -maxdepth 1 -type d | wc -l | awk '{print $1}'
}

update_json_mcp_config() {
    local file="$1"
    if [ -f "$file" ]; then
        node "$REPO_DIR/scripts/update-mcp-config.js" "$file"
    fi
}


if [ "$INSTALL_CLAUDE" = "1" ]; then
    # --- Claude Code ---
    info "Setting up Claude Code..."

    mkdir -p "$CLAUDE_DIR"/{agents,skills,rules/ecc,hooks}

    # CLAUDE.md
    copy_config "$REPO_DIR/claude/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"
    ok "CLAUDE.md"

    # settings.json
    copy_config "$REPO_DIR/claude/settings.json" "$CLAUDE_DIR/settings.json"
    ok "settings.json"

    # RTK.md
    copy_config "$REPO_DIR/claude/RTK.md" "$CLAUDE_DIR/RTK.md"
    ok "RTK.md"

    # Agents (written directly by compiler)
    ok "Agents ($(count_files "$CLAUDE_DIR/agents" "*.md") files)"

    # Skills
    for d in "$REPO_DIR"/skills/*/; do
        name="$(basename "$d")"
        copy_config "$d" "$CLAUDE_DIR/skills/$name"
    done
    ok "Skills ($(count_dirs "$REPO_DIR/skills") dirs)"

    # Rules (ECC only)
    for f in "$REPO_DIR"/claude/rules/ecc/*.md; do
        name="$(basename "$f")"
        copy_config "$f" "$CLAUDE_DIR/rules/ecc/$name"
    done
    ok "Rules ($(count_files "$REPO_DIR/claude/rules/ecc" "*.md") files)"

    # Hooks
    if [ -d "$REPO_DIR/claude/hooks" ]; then
        hooks_linked=0
        for f in "$REPO_DIR"/claude/hooks/*; do
            if [ -f "$f" ]; then
                name="$(basename "$f")"
                copy_config "$f" "$CLAUDE_DIR/hooks/$name"
                hooks_linked=$((hooks_linked + 1))
            fi
        done
        if [ $hooks_linked -gt 0 ]; then
            ok "Hooks ($hooks_linked files)"
        fi
    fi
fi

if [ "$INSTALL_CODEX" = "1" ]; then
    # --- Codex CLI ---
    info "Setting up Codex CLI..."

    mkdir -p "$CODEX_DIR"/{agents,skills}

    # AGENTS.md
    copy_config "$REPO_DIR/codex/AGENTS.md" "$CODEX_DIR/AGENTS.md"
    ok "AGENTS.md"

    # RTK.md
    copy_config "$REPO_DIR/codex/RTK.md" "$CODEX_DIR/RTK.md"
    ok "RTK.md"
    configure_rtk

    # config.toml
    install_local_config "$REPO_DIR/codex/config.toml" "$CODEX_DIR/config.toml"
    ok "config.toml"
    configure_codex_trusted_projects "$CODEX_DIR/config.toml"

    # Agents (written directly by compiler)
    ok "Agents ($(count_files "$CODEX_DIR/agents" "*.toml") files)"

    # Skills
    for d in "$REPO_DIR"/skills/*/; do
        name="$(basename "$d")"
        copy_config "$d" "$CODEX_DIR/skills/$name"
    done
    ok "Skills ($(count_dirs "$REPO_DIR/skills") dirs)"
fi

if [ "$INSTALL_AGY" = "1" ]; then
    # --- Antigravity CLI (agy) ---
    info "Setting up Antigravity CLI (agy)..."

    if [ -L "$HOME/.gemini/config/skills" ]; then
        ok "Skills directory is already symlinked for agy"
    else
        mkdir -p "$HOME/.gemini/config/skills"
        for d in "$REPO_DIR"/skills/*/; do
            name="$(basename "$d")"
            copy_config "$d" "$HOME/.gemini/config/skills/$name"
        done
        ok "Skills ($(count_dirs "$REPO_DIR/skills") dirs) linked to agy config"
    fi

    if [ -L "$HOME/.gemini/config/agents" ]; then
        rm -f "$HOME/.gemini/config/agents"
    fi
    mkdir -p "$HOME/.gemini/config/agents"
    ok "Agents ($(count_files "$HOME/.gemini/config/agents" "*.md") files) configured for agy"

    # ANTIGRAVITY.md
    copy_config "$REPO_DIR/gemini/ANTIGRAVITY.md" "$HOME/.gemini/config/ANTIGRAVITY.md"
    ok "ANTIGRAVITY.md"

    # settings.json
    mkdir -p "$HOME/.gemini/antigravity-cli"
    copy_config "$REPO_DIR/gemini/settings.json" "$HOME/.gemini/antigravity-cli/settings.json"
    ok "settings.json"
fi


# Update Playwright MCP configurations for all three CLIs (Claude, agy, Codex)
if [ "$INSTALL_CLAUDE" = "1" ] || [ "$INSTALL_AGY" = "1" ]; then
    info "Ensuring Playwright MCP runs with --isolated..."
    if [ "$INSTALL_CLAUDE" = "1" ]; then
        update_json_mcp_config "$HOME/.claude.json"
        update_json_mcp_config "$HOME/.claude/ecc-source/mcp-configs/mcp-servers.json"
    fi
    if [ "$INSTALL_AGY" = "1" ]; then
        update_json_mcp_config "$HOME/.gemini/config/mcp_config.json"
    fi
fi

# Sync disabled MCP servers from shared-disabled-mcp.json
if [ -f "$REPO_DIR/shared-disabled-mcp.json" ] && [ -f "$REPO_DIR/scripts/mcp-toggle.py" ]; then
    info "Syncing MCP server states..."
    python3 "$REPO_DIR/scripts/mcp-toggle.py" sync 2>/dev/null || true
fi

echo ""
echo "Done! Restart Claude Code / Codex CLI / agy to pick up changes."
echo ""
echo "NOTE: Re-run ./install.sh any time to refresh shared assets."
echo "      Personal Codex trusted projects stay in ~/.codex/config.toml."
