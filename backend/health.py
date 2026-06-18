import subprocess
from datetime import datetime
from pathlib import Path
from .constants import REPO_DIR

def get_graphify_build_commit() -> str | None:
    report_path = REPO_DIR / "graphify-out" / "GRAPH_REPORT.md"
    if not report_path.exists():
        return None
    try:
        with report_path.open(encoding="utf-8") as f:
            for line in f:
                if "Built from commit:" in line:
                    parts = line.split("Built from commit:")
                    if len(parts) > 1:
                        return parts[1].replace("`", "").strip()
    except Exception:
        pass
    return None

def get_git_commit() -> str | None:
    try:
        res = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=str(REPO_DIR))
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return None

def get_graphify_health() -> dict:
    graph_json = REPO_DIR / "graphify-out" / "graph.json"
    graph_exists = graph_json.exists()
    
    graph_size_kb = 0.0
    last_built = "N/A"
    if graph_exists:
        try:
            graph_size_kb = round(graph_json.stat().st_size / 1024.0, 2)
            mtime = graph_json.stat().st_mtime
            last_built = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
            
    commit_hook = REPO_DIR / ".git" / "hooks" / "post-commit"
    checkout_hook = REPO_DIR / ".git" / "hooks" / "post-checkout"
    git_hooks_installed = commit_hook.exists() and checkout_hook.exists()
    
    build_commit = get_graphify_build_commit()
    current_commit = get_git_commit()
    
    is_stale = False
    stale_reason = None
    if graph_exists:
        if build_commit and current_commit:
            b_comm = build_commit.lower()
            c_comm = current_commit.lower()
            if not (b_comm.startswith(c_comm) or c_comm.startswith(b_comm)):
                is_stale = True
                stale_reason = f"Graph built from commit {build_commit}, but active workspace commit is {current_commit}."
        elif not build_commit:
            is_stale = True
            stale_reason = "No build commit found in GRAPH_REPORT.md."
            
    return {
        "graph_exists": graph_exists,
        "graph_size_kb": graph_size_kb,
        "git_hooks_installed": git_hooks_installed,
        "build_commit": build_commit or "N/A",
        "current_commit": current_commit or "N/A",
        "is_stale": is_stale,
        "stale_reason": stale_reason or "",
        "last_built": last_built
    }
