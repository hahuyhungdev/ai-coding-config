"""File operations for installer."""

import filecmp
import json
import shutil
import subprocess
import sys
from pathlib import Path

from .cli import info, ok, warn, error, run_node_script


def merge_json(source: Path, target: Path) -> bool:
    """Deep-merge JSON: repo keys are base, target-only keys are preserved.

    Returns True if merged/written, False if skipped.
    """
    if not source.exists():
        warn(f"Source does not exist: {source}")
        return False

    try:
        with open(source, "r", encoding="utf-8") as f:
            repo = json.load(f)
    except Exception as e:
        error(f"Failed to read source JSON: {e}")
        return False

    if not target.exists():
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                json.dump(repo, f, indent=2)
                f.write("\n")
            return True
        except Exception as e:
            error(f"Failed to write target JSON: {e}")
            return False

    try:
        with open(target, "r", encoding="utf-8") as f:
            existing = json.load(f)
    except Exception as e:
        error(f"Failed to read target JSON: {e}")
        return False

    def deep_merge(base: dict, override: dict) -> dict:
        merged = dict(base)
        for k, v in override.items():
            if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
                merged[k] = deep_merge(merged[k], v)
            else:
                merged[k] = v
        return merged

    merged = deep_merge(repo, existing)

    try:
        with open(target, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)
            f.write("\n")
        return True
    except Exception as e:
        error(f"Failed to write merged JSON: {e}")
        return False


def copy_config(source: Path, target: Path, force: bool = False) -> bool:
    """Copy config from repo to global with conflict detection.

    Returns True if copied, False if skipped.
    """
    if not source.exists():
        warn(f"Source does not exist: {source}")
        return False

    # Remove old symlink (from previous installs)
    if target.is_symlink():
        target.unlink()

    # Target doesn't exist → copy directly
    if not target.exists():
        try:
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            return True
        except Exception as e:
            error(f"Failed to copy {source} to {target}: {e}")
            return False

    # Target exists → check for differences
    is_same = False
    if source.is_dir() and target.is_dir():
        dircmp = filecmp.dircmp(source, target)
        is_same = not dircmp.left_only and not dircmp.right_only and not dircmp.diff_files
    elif source.is_file() and target.is_file():
        is_same = filecmp.cmp(source, target, shallow=False)

    if is_same:
        return True  # Same, skip

    # Conflict detected
    print()
    warn(f"Conflict detected: {target.name}")
    print(f"  Repo:   {source}")
    print(f"  Global: {target}")

    if force:
        try:
            if target.is_dir():
                shutil.rmtree(target)
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
            ok(f"Overwritten (force): {target.name}")
            return True
        except Exception as e:
            error(f"Failed to overwrite {target}: {e}")
            return False

    if sys.stdin.isatty():
        # Interactive: show diff and ask
        if source.is_file() and target.is_file():
            print()
            try:
                subprocess.run(
                    ["diff", "--color=auto", str(source), str(target)],
                    capture_output=False,
                )
            except Exception:
                pass
        elif source.is_dir() and target.is_dir():
            print()
            try:
                subprocess.run(
                    ["diff", "-rq", str(source), str(target)],
                    capture_output=False,
                )
            except Exception:
                pass

        print()
        print("  [o] Overwrite  [k] Keep current  [s] Skip")
        try:
            choice = input("  Choice: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            choice = "s"

        try:
            if choice == "o":
                if target.is_dir():
                    shutil.rmtree(target)
                    shutil.copytree(source, target)
                else:
                    shutil.copy2(source, target)
                ok(f"Overwritten: {target.name}")
                return True
            elif choice == "k":
                ok(f"Kept current: {target.name}")
                return False
            else:
                ok(f"Skipped: {target.name}")
                return False
        except Exception as e:
            error(f"Failed to handle choice: {e}")
            return False
    else:
        # Non-interactive: skip with warning
        warn(f"Skipping conflict (non-interactive): {target.name}")
        warn("Use --force to overwrite all")
        return False


def install_local_config(source: Path, target: Path, force: bool = False) -> bool:
    """Install config with merge support (for TOML files)."""
    # Remove old symlink
    if target.is_symlink():
        warn(f"{target.name} is symlinked - replacing with copy")
        target.unlink()
        try:
            shutil.copy2(source, target)
            return True
        except Exception as e:
            error(f"Failed to replace symlink: {e}")
            return False

    if target.exists():
        if filecmp.cmp(source, target, shallow=False):
            return True  # Same, skip
        info(f"Merging {source.name} configurations into {target}...")
        run_node_script("merge-toml-config.js", str(source), str(target))
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
    """Count subdirectories in directory."""
    if not directory.exists():
        return 0
    return len([d for d in directory.iterdir() if d.is_dir()])
