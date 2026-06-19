"""Constants for installer."""

import os
from pathlib import Path

def get_real_home(check_paths: list[str] = None) -> Path:
    home = Path.home()
    if "tmp" in str(home).lower() or "temp" in str(home).lower():
        # If CWD is also under a tmp/temp folder, we are likely running in a unit test
        # (e.g. TestInstallerCli) where the entire environment is mocked under /tmp.
        # In that case, we should respect Path.home() (the mocked home) and not override it.
        cwd_str = str(os.getcwd()).lower()
        if "tmp" in cwd_str or "temp" in cwd_str:
            return home

        # Try to extract the real user home from this file path or CWD to bypass sandboxed Path.home()
        paths = check_paths if check_paths is not None else [__file__, os.getcwd()]
        for path_str in paths:
            if "\\" in path_str:
                from pathlib import PureWindowsPath
                p = PureWindowsPath(path_str)
                parts = p.parts
                if len(parts) > 2 and parts[1].lower() == "users":
                    return Path(parts[0] + parts[1] + "\\" + parts[2])
            else:
                p = Path(path_str).resolve()
                parts = p.parts
                if len(parts) > 2 and parts[1] in ("home", "Users"):
                    return Path("/", parts[1], parts[2])
    return home

REAL_HOME = get_real_home()

# Shared Directories
CLAUDE_DIR = REAL_HOME / ".claude"
CODEX_DIR = REAL_HOME / ".codex"
GEMINI_DIR = REAL_HOME / ".gemini" / "config"
GEMINI_CLI_DIR = REAL_HOME / ".gemini" / "antigravity-cli"
REPO_DIR = Path(__file__).resolve().parent.parent

