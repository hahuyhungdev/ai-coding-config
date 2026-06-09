"""CLI utilities for installer."""

import subprocess
import sys
from pathlib import Path

# Colors
GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
DIM = "\033[2m"
RESET = "\033[0m"

REPO_DIR = Path(__file__).resolve().parent.parent


def info(msg: str) -> None:
    """Print info message."""
    print(f"{BLUE}[INFO]{RESET} {msg}")


def ok(msg: str) -> None:
    """Print success message."""
    print(f"{GREEN}[OK]{RESET} {msg}")


def warn(msg: str) -> None:
    """Print warning message."""
    print(f"{YELLOW}[WARN]{RESET} {msg}")


def error(msg: str) -> None:
    """Print error message."""
    print(f"{RED}[ERROR]{RESET} {msg}")


def run_script(script: str, *args: str) -> bool:
    """Run a script from the scripts directory."""
    script_path = REPO_DIR / "scripts" / script
    if not script_path.exists():
        warn(f"Script not found: {script}")
        return False
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), *args],
            capture_output=True,
            text=True,
        )
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return result.returncode == 0
    except Exception as e:
        warn(f"Failed to run {script}: {e}")
        return False


def run_node_script(script: str, *args: str) -> bool:
    """Run a Node.js script from the scripts directory."""
    script_path = REPO_DIR / "scripts" / script
    if not script_path.exists():
        warn(f"Script not found: {script}")
        return False
    try:
        result = subprocess.run(
            ["node", str(script_path), *args],
            capture_output=True,
            text=True,
        )
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return result.returncode == 0
    except Exception as e:
        warn(f"Failed to run {script}: {e}")
        return False
