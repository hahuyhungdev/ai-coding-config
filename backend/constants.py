from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
SHARED_DISABLED = REPO_DIR / "shared-disabled-mcp.json"
AGENTS_DIR = REPO_DIR / "agents"
SKILLS_DIR = REPO_DIR / "skills"

BRAIN_DIR = Path.home() / ".gemini" / "antigravity-cli" / "brain"
CLAUDE_DIR = Path.home() / ".claude" / "projects"
CODEX_DIR = Path.home() / ".codex" / "sessions"

CLI_CONFIGS = {
    "claude": {"name": "Claude Code", "dir": "~/.claude"},
    "codex": {"name": "Codex CLI", "dir": "~/.codex"},
    "agy": {"name": "Antigravity", "dir": "~/.gemini"},
}

ANALYTICS_CACHE = {}
