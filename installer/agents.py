"""Agent compilation for installer."""

from pathlib import Path

from .cli import info, ok, warn, error

# Directories
REPO_DIR = Path(__file__).resolve().parent.parent
CLAUDE_DIR = Path.home() / ".claude"


def compile_agents(install_claude: bool, install_codex: bool, install_agy: bool) -> None:
    """Compile custom agents."""
    info("Compiling custom agents...")

    agents_source = REPO_DIR / "agents"
    if not agents_source.exists():
        warn("Agents directory not found")
        return

    # Count agents
    agent_files = list(agents_source.glob("*.md"))
    info(f"Found {len(agent_files)} agent source files. Starting compilation...")

    # Copy agents to Claude directory
    if install_claude:
        agents_target = CLAUDE_DIR / "agents"
        agents_target.mkdir(parents=True, exist_ok=True)

        for agent_file in agent_files:
            target = agents_target / agent_file.name
            try:
                import shutil
                shutil.copy2(agent_file, target)
            except Exception as e:
                warn(f"Failed to copy agent {agent_file.name}: {e}")

        ok("Agent compilation complete!")
    else:
        info("Skipping agent compilation (Claude not selected)")
