"""File operations for installer."""

import filecmp
import json
import shutil
from pathlib import Path

from .cli import info, ok, warn, error


def merge_json(source: Path, target: Path) -> bool:
    """Merge JSON source into target, preserving existing keys."""
    try:
        with open(source, 'r') as f:
            source_data = json.load(f)
    except Exception as e:
        error(f"Failed to read source JSON: {e}")
        return False

    if target.exists():
        try:
            with open(target, 'r') as f:
                target_data = json.load(f)
        except Exception as e:
            error(f"Failed to read target JSON: {e}")
            return False
    else:
        target_data = {}

    # Deep merge
    def deep_merge(base: dict, update: dict) -> dict:
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    merged = deep_merge(target_data, source_data)

    try:
        with open(target, 'w') as f:
            json.dump(merged, f, indent=2)
            f.write('\n')
        return True
    except Exception as e:
        error(f"Failed to write target JSON: {e}")
        return False


def copy_config(source: Path, target: Path, force: bool = False) -> bool:
    """Copy configuration file or directory."""
    if not source.exists():
        warn(f"Source not found: {source}")
        return False

    if target.exists() and not force:
        if filecmp.cmp(source, target):
            info(f"Already up to date: {target.name}")
            return True
        else:
            warn(f"File exists: {target.name}")
            return False

    try:
        if source.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        return True
    except Exception as e:
        error(f"Failed to copy {source} to {target}: {e}")
        return False


def install_local_config(source: Path, target: Path, force: bool = False) -> bool:
    """Install local configuration file."""
    if not source.exists():
        warn(f"Source not found: {source}")
        return False

    if target.exists() and not force:
        info(f"Already exists: {target.name}")
        return True

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return True
    except Exception as e:
        error(f"Failed to install {source} to {target}: {e}")
        return False


def count_files(directory: Path, pattern: str) -> int:
    """Count files matching pattern in directory."""
    if not directory.exists():
        return 0
    return len(list(directory.glob(pattern)))


def count_dirs(directory: Path) -> int:
    """Count directories in directory."""
    if not directory.exists():
        return 0
    return len([d for d in directory.iterdir() if d.is_dir()])
