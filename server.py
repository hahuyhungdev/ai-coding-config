#!/usr/bin/env python3
import json
import subprocess
import sys
import argparse
import urllib.parse
import urllib.request
import shutil
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import toml

REPO_DIR = Path(__file__).resolve().parent
SHARED_DISABLED = REPO_DIR / "shared-disabled-mcp.json"
AGENTS_DIR = REPO_DIR / "agents"
SKILLS_DIR = REPO_DIR / "skills"

CLI_CONFIGS = {
    "claude": {"name": "Claude Code", "dir": "~/.claude"},
    "codex": {"name": "Codex CLI", "dir": "~/.codex"},
    "agy": {"name": "Antigravity", "dir": "~/.gemini"},
}


def get_all_mcp_servers() -> list[str]:
    defaults_path = REPO_DIR / "scripts" / "update-mcp-config.js"
    if defaults_path.exists():
        content = defaults_path.read_text()
        import re
        block = re.search(r'defaultServers\s*=\s*\{(.+?)\n\s*\};', content, re.DOTALL)
        if block:
            matches = re.findall(r'(?:\"([^\"]+)\"|\'([^\']+)\'|(\w[\w-]*))\s*:\s*\{', block.group(1))
            servers = [m[0] or m[1] or m[2] for m in matches]
            if servers:
                return servers
    return ["playwright", "context7", "memory", "sequential-thinking", "postgres", "sqlite", "docker", "aws"]


def load_disabled() -> list[str]:
    try:
        with open(SHARED_DISABLED) as f:
            return json.load(f).get("disabledMcpServers", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_disabled(disabled: list[str]) -> None:
    with open(SHARED_DISABLED, "w") as f:
        json.dump({"disabledMcpServers": sorted(disabled)}, f, indent=2)
        f.write("\n")


def get_mcp_servers() -> dict:
    try:
        with open(Path.home() / ".claude.json") as f:
            data = json.load(f)
            configs = {}
            configs.update(data.get("disabledMcpServers", {}))
            configs.update(data.get("mcpServers", {}))
            return configs
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_mcp_configs(updated_configs: dict, disabled_list: list[str]) -> None:
    claude_json_path = Path.home() / ".claude.json"
    try:
        data = {}
        if claude_json_path.exists():
            with open(claude_json_path) as f:
                data = json.load(f)
        
        mcp_servers = {}
        disabled_mcp_servers = {}
        
        for name, config in updated_configs.items():
            if name in disabled_list:
                disabled_mcp_servers[name] = config
            else:
                mcp_servers[name] = config
                
        data["mcpServers"] = mcp_servers
        data["disabledMcpServers"] = disabled_mcp_servers
        
        with open(claude_json_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    except Exception as e:
        print(f"Error saving MCP configs: {e}")


def list_agents() -> list[str]:
    if AGENTS_DIR.exists():
        return sorted([f.stem for f in AGENTS_DIR.glob("*.md")])
    return []


def list_skills() -> list[str]:
    if SKILLS_DIR.exists():
        return sorted([d.name for d in SKILLS_DIR.iterdir() if d.is_dir()])
    return []


def parse_markdown_frontmatter(path: Path) -> dict:
    if not path.exists():
        return {}
    metadata = {}
    try:
        content = path.read_text()
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        metadata[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return metadata


def load_claude_settings() -> dict:
    template_path = REPO_DIR / "claude" / "settings.json"
    try:
        with open(template_path) as f:
            return json.load(f)
    except Exception:
        return {}


def save_claude_settings(data: dict) -> None:
    template_path = REPO_DIR / "claude" / "settings.json"
    try:
        with open(template_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    except Exception:
        pass


def load_gemini_settings() -> dict:
    template_path = REPO_DIR / "gemini" / "settings.json"
    try:
        with open(template_path) as f:
            return json.load(f)
    except Exception:
        return {}


def save_gemini_settings(data: dict) -> None:
    template_path = REPO_DIR / "gemini" / "settings.json"
    try:
        with open(template_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    except Exception:
        pass



def load_codex_settings() -> dict:
    template_path = REPO_DIR / "codex" / "config.toml"
    try:
        with open(template_path) as f:
            return toml.load(f)
    except Exception:
        return {}


def update_toml_value(file_path: Path, section: str | None, key: str, value: any) -> None:
    if not file_path.exists():
        return
    lines = file_path.read_text().splitlines()
    
    current_section = None
    updated = False
    
    if isinstance(value, str):
        new_value_str = f'"{value}"'
    elif isinstance(value, bool):
        new_value_str = "true" if value else "false"
    else:
        new_value_str = str(value)
        
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped[1:-1].strip()
            continue
            
        if current_section == section:
            if "=" in line:
                parts = line.split("=", 1)
                k = parts[0].strip()
                if k == key:
                    comment = ""
                    if "#" in parts[1]:
                        comment = "  " + parts[1].split("#", 1)[1]
                    line_comment = f" #{comment}" if comment else ""
                    lines[i] = f"{parts[0].split('=')[0]}= {new_value_str}{line_comment}"
                    updated = True
                    break
                    
    if updated:
        file_path.write_text("\n".join(lines) + "\n")


def get_targets_state() -> dict:
    cli_state = {}
    for cid, info in CLI_CONFIGS.items():
        path_str = info["dir"].replace("~", str(Path.home()))
        cli_state[cid] = Path(path_str).exists()
    
    if not any(cli_state.values()):
        cli_state = {cid: True for cid in CLI_CONFIGS}
    return cli_state


class ConfigHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to suppress standard HTTP logging to keep console clean
        pass

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)
        
        # Static files serving for compiled Vite React app (frontend/dist/)
        dist_dir = REPO_DIR / "frontend" / "dist"
        
        # Resolve target file path inside dist
        rel_path = path.lstrip("/")
        if not rel_path or rel_path == "index.html":
            file_to_serve = dist_dir / "index.html"
        else:
            file_to_serve = dist_dir / rel_path
            
        # If the file exists in dist, serve it
        if dist_dir.exists() and file_to_serve.exists() and file_to_serve.is_file() and dist_dir in file_to_serve.resolve().parents:
            self.send_response(200)
            if file_to_serve.suffix == ".html":
                self.send_header("Content-Type", "text/html")
            elif file_to_serve.suffix == ".js":
                self.send_header("Content-Type", "application/javascript")
            elif file_to_serve.suffix == ".css":
                self.send_header("Content-Type", "text/css")
            elif file_to_serve.suffix == ".svg":
                self.send_header("Content-Type", "image/svg+xml")
            elif file_to_serve.suffix == ".png":
                self.send_header("Content-Type", "image/png")
            elif file_to_serve.suffix == ".json":
                self.send_header("Content-Type", "application/json")
            else:
                self.send_header("Content-Type", "application/octet-stream")
            self.end_headers()
            self.wfile.write(file_to_serve.read_bytes())
            return
            
        # Fallback to root index.html if dist doesn't exist and path is root
        if (path == "/" or path == "/index.html") and not dist_dir.exists():
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write((REPO_DIR / "index.html").read_bytes())
            return
            
        if path == "/api/config":
            try:
                config_data = {
                    "claude": load_claude_settings(),
                    "codex": load_codex_settings(),
                    "gemini": load_gemini_settings(),
                    "mcp_servers": get_mcp_servers(),

                    "all_mcp": get_all_mcp_servers(),
                    "disabled_mcp": load_disabled(),
                    "gemini_instructions": (REPO_DIR / "gemini" / "ANTIGRAVITY.md").read_text() if (REPO_DIR / "gemini" / "ANTIGRAVITY.md").exists() else "",
                    "claude_instructions": (REPO_DIR / "claude" / "CLAUDE.md").read_text() if (REPO_DIR / "claude" / "CLAUDE.md").exists() else "",
                    "codex_instructions": (REPO_DIR / "codex" / "AGENTS.md").read_text() if (REPO_DIR / "codex" / "AGENTS.md").exists() else "",
                    "targets": get_targets_state(),
                    "agents": list_agents(),
                    "skills": list_skills()
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(config_data).encode("utf-8"))
            except Exception as e:
                self.send_error_json(500, str(e))
                
        elif path.startswith("/api/agent/"):
            name = path.replace("/api/agent/", "")
            agent_file = AGENTS_DIR / f"{name}.md"
            if not agent_file.exists():
                self.send_error_json(404, "Agent not found")
                return
            try:
                content = agent_file.read_text()
                metadata = parse_markdown_frontmatter(agent_file)
                prompt = content
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        prompt = parts[2].strip()
                res = {"name": name, "metadata": metadata, "prompt": prompt}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(res).encode("utf-8"))
            except Exception as e:
                self.send_error_json(500, str(e))
                
        elif path.startswith("/api/skill/"):
            name = path.replace("/api/skill/", "")
            skill_file = SKILLS_DIR / name / "SKILL.md"
            if not skill_file.exists():
                self.send_error_json(404, "Skill not found")
                return
            try:
                content = skill_file.read_text()
                metadata = parse_markdown_frontmatter(skill_file)
                prompt = content
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        prompt = parts[2].strip()
                res = {"name": name, "metadata": metadata, "prompt": prompt}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(res).encode("utf-8"))
            except Exception as e:
                self.send_error_json(500, str(e))
                
        elif path == "/api/apply/stream":
            force = query.get("force", ["false"])[0] == "true"
            claude = query.get("claude", ["true"])[0] == "true"
            codex = query.get("codex", ["true"])[0] == "true"
            agy = query.get("agy", ["true"])[0] == "true"
            
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            
            self.send_sse_line("🚀 Starting installation process...")
            args = [sys.executable, "-u", str(REPO_DIR / "install.py")]
            targets = []
            if claude: targets.append("--claude")
            if codex: targets.append("--codex")
            if agy: targets.append("--agy")
            
            if targets:
                args.extend(targets)
            else:
                args.append("--none")
                
            if force:
                args.append("--force")
                
            self.send_sse_line(f"Command: {' '.join(args)}")
            try:
                p = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                for line in iter(p.stdout.readline, ""):
                    self.send_sse_line(line.rstrip())
                p.wait()
                if p.returncode == 0:
                    self.send_sse_line("SUCCESS: ✓ Done! All changes saved and applied successfully.")
                else:
                    self.send_sse_line(f"ERROR: ✘ Apply failed with exit code {p.returncode}. Changes remain staged.")
            except Exception as e:
                self.send_sse_line(f"ERROR: ✘ Error running installer: {e}")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        if path == "/api/save-temp":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                
                # 1. Save Claude
                save_claude_settings(payload.get("claude", {}))

                # 1.5. Save Gemini
                save_gemini_settings(payload.get("gemini", {}))

                # 2. Save Codex

                template_path = REPO_DIR / "codex" / "config.toml"
                codex_data = payload.get("codex", {})
                update_toml_value(template_path, None, "approval_policy", codex_data.get("approval_policy", "on-request"))
                update_toml_value(template_path, None, "sandbox_mode", codex_data.get("sandbox_mode", "workspace-write"))
                update_toml_value(template_path, None, "web_search", codex_data.get("web_search", "live"))
                update_toml_value(template_path, None, "approvals_reviewer", codex_data.get("approvals_reviewer", "user"))
                update_toml_value(template_path, None, "model", codex_data.get("model", "gpt-5.5"))
                update_toml_value(template_path, None, "model_reasoning_effort", codex_data.get("model_reasoning_effort", "medium"))
                update_toml_value(template_path, None, "persistent_instructions", codex_data.get("persistent_instructions", ""))
                
                features = codex_data.get("features", {})
                update_toml_value(template_path, "features", "memories", features.get("memories", True))
                update_toml_value(template_path, "features", "multi_agent", features.get("multi_agent", True))
                
                notice = codex_data.get("notice", {})
                update_toml_value(template_path, "notice", "hide_full_access_warning", notice.get("hide_full_access_warning", True))
                update_toml_value(template_path, "notice", "fast_default_opt_out", notice.get("fast_default_opt_out", True))

                # 3. Save disabled MCPs
                save_disabled(payload.get("disabled_mcp", []))

                # 4. Save Gemini, Claude, and Codex instructions
                (REPO_DIR / "gemini" / "ANTIGRAVITY.md").write_text(payload.get("gemini_instructions", ""))
                (REPO_DIR / "claude" / "CLAUDE.md").write_text(payload.get("claude_instructions", ""))
                (REPO_DIR / "codex" / "AGENTS.md").write_text(payload.get("codex_instructions", ""))

                # 5. Save MCP configurations directly to ~/.claude.json
                save_mcp_configs(payload.get("mcp_servers", {}), payload.get("disabled_mcp", []))

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Settings saved to templates"}).encode("utf-8"))
            except Exception as e:
                self.send_error_json(500, str(e))
        elif path == "/api/mcp/test":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                name = payload.get("name", "unknown")
                mcp_type = payload.get("type", "stdio")
                
                if mcp_type == "sse":
                    url = payload.get("url", "").strip()
                    if not url:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "message": "Error: SSE URL is empty."}).encode("utf-8"))
                        return
                    
                    try:
                        req = urllib.request.Request(url, method="GET")
                        req.add_header("User-Agent", "Mozilla/5.0 (AI Config Dashboard)")
                        with urllib.request.urlopen(req, timeout=3.0) as r:
                            self.send_response(200)
                            self.send_header("Content-Type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps({
                                "status": "success", 
                                "message": f"Successfully connected to SSE URL (HTTP {r.status})"
                            }).encode("utf-8"))
                    except Exception as conn_err:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "status": "error", 
                            "message": f"Connection failed: {conn_err}"
                        }).encode("utf-8"))
                else:
                    command = payload.get("command", "").strip()
                    if not command:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "message": "Error: Command is empty."}).encode("utf-8"))
                        return
                    
                    resolved_cmd = shutil.which(command)
                    if not resolved_cmd:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "status": "error", 
                            "message": f"Command '{command}' not found in system PATH."
                        }).encode("utf-8"))
                    else:
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
                            
                            self.send_response(200)
                            self.send_header("Content-Type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps({
                                "status": "success",
                                "message": f"Command '{command}' is available and executable!{version_str}"
                            }).encode("utf-8"))
                        except subprocess.TimeoutExpired:
                            self.send_response(200)
                            self.send_header("Content-Type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps({
                                "status": "success",
                                "message": f"Command '{command}' is available (launch test timed out)."
                            }).encode("utf-8"))
                        except Exception as exec_err:
                            self.send_response(200)
                            self.send_header("Content-Type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps({
                                "status": "warning",
                                "message": f"Command found at {resolved_cmd}, but execution test failed: {exec_err}"
                            }).encode("utf-8"))
            except Exception as e:
                self.send_error_json(500, str(e))
        else:
            self.send_response(404)
            self.end_headers()

    def send_sse_line(self, data: str):
        try:
            self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
            self.wfile.flush()
        except (ConnectionResetError, BrokenPipeError):
            pass

    def send_error_json(self, code: int, message: str):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"detail": message}).encode("utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Configuration Web Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the web server on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address to run the web server on")
    args = parser.parse_args()
    
    server_address = (args.host, args.port)
    httpd = ThreadingHTTPServer(server_address, ConfigHandler)
    
    print(f"Starting standard library web server on http://{args.host}:{args.port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        sys.exit(0)
