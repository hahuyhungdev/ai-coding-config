import subprocess
import shutil
import urllib.request
from pathlib import Path

def resolve_project_dir(project_name: str) -> Path | None:
    """Find the project directory by checking common parent locations."""
    search_paths = [
        Path.home() / "projects" / "company" / project_name,
        Path.home() / "projects" / "personals" / project_name,
        Path.home() / "projects" / project_name
    ]
    for p in search_paths:
        if p.exists() and p.is_dir():
            return p
    return None

def generate_graphify_view(project_dir: Path, view_type: str, project_name: str) -> tuple[Path | None, str | None]:
    """Generate Graphify trees/callflows if needed and return target path or error message."""
    if view_type == "graph":
        filename = "graph.html"
    elif view_type == "tree":
        filename = "GRAPH_TREE.html"
        file_path = project_dir / "graphify-out" / filename
        if not file_path.exists():
            subprocess.run(["graphify", "tree"], cwd=str(project_dir), capture_output=True)
    elif view_type == "callflow":
        filename = f"{project_name}-callflow.html"
        file_path = project_dir / "graphify-out" / filename
        if not file_path.exists():
            subprocess.run(["graphify", "export", "callflow-html"], cwd=str(project_dir), capture_output=True)
    else:
        filename = "graph.html"
    
    file_path = project_dir / "graphify-out" / filename
    if not file_path.exists():
        return None, f"Graph visualization file '{filename}' not found in project '{project_name}'"
    return file_path, None

def run_graphify_update(project_dir: Path, force: bool = False) -> dict:
    """Run `graphify update` command inside the specified project directory."""
    cmd = ["graphify", "update", "."]
    if force:
        cmd.append("--force")
    
    result = subprocess.run(cmd, cwd=str(project_dir), capture_output=True, text=True)
    return {
        "status": "success" if result.returncode == 0 else "error",
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }

def execute_simulator_command(cmd_line: str, repo_dir: Path) -> dict:
    """Safely run a command inside repository root with a strict timeout limit."""
    try:
        proc = subprocess.run(
            cmd_line,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5.0,
            cwd=str(repo_dir)
        )
        stdout_str = proc.stdout.decode("utf-8", errors="replace")
        stderr_str = proc.stderr.decode("utf-8", errors="replace")
        output = stdout_str + stderr_str
        
        return {
            "status": "success" if proc.returncode == 0 else "error",
            "output": output or "[No output generated]"
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Command execution timed out (5s limit)."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def read_simulator_file(file_path: Path) -> dict:
    """Read first 15 lines of a file for simulation purposes."""
    resolved_path = Path(file_path).resolve()
    if not resolved_path.exists() or not resolved_path.is_file():
        return {"status": "error", "message": f"File '{file_path}' does not exist or is not a file."}
    
    try:
        with open(resolved_path, "r", encoding="utf-8") as f:
            lines = [f.readline() for _ in range(15)]
            content = "".join(lines)
            if f.readline():
                content += "\n... (truncated)"
        return {"status": "success", "output": content}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def test_mcp_server(payload: dict) -> dict:
    """Validate MCP stdio binary executable or SSE server connectivity."""
    mcp_type = payload.get("type", "stdio")
    
    if mcp_type == "sse":
        url = payload.get("url", "").strip()
        if not url:
            return {"status": "error", "message": "Error: SSE URL is empty."}
        
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("User-Agent", "Mozilla/5.0 (AI Config Dashboard)")
            with urllib.request.urlopen(req, timeout=3.0) as r:
                return {
                    "status": "success", 
                    "message": f"Successfully connected to SSE URL (HTTP {r.status})"
                }
        except Exception as conn_err:
            return {
                "status": "error", 
                "message": f"Connection failed: {conn_err}"
            }
    else:
        command = payload.get("command", "").strip()
        if not command:
            return {"status": "error", "message": "Error: Command is empty."}
        
        resolved_cmd = shutil.which(command)
        if not resolved_cmd:
            return {
                "status": "error", 
                "message": f"Command '{command}' not found in system PATH."
            }
        
        try:
            test_args = [command]
            if command in ["npx", "uvx", "node", "python", "python3", "pip", "npm"]:
                test_args.append("--version")
            
            proc = subprocess.run(
                test_args, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                timeout=2.0
            )
            version_info = proc.stdout.decode("utf-8").strip() or proc.stderr.decode("utf-8").strip()
            version_str = f" ({version_info[:30]}...)" if version_info else ""
            
            return {
                "status": "success",
                "message": f"Command '{command}' is available and executable!{version_str}"
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "success",
                "message": f"Command '{command}' is available (launch test timed out)."
            }
        except Exception as exec_err:
            return {
                "status": "warning",
                "message": f"Command found at {resolved_cmd}, but execution test failed: {exec_err}"
            }
