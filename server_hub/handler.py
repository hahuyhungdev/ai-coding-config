import json
import subprocess
import sys
import urllib.parse
import urllib.request
import shutil
import os
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from .constants import REPO_DIR, BRAIN_DIR, CLAUDE_DIR, CODEX_DIR, AGENTS_DIR, SKILLS_DIR
from .parsers import parse_gemini_jsonl, parse_claude_jsonl, parse_codex_jsonl
from .metadata import get_all_conversations
from .token_estimator import estimate_tokens
from .analytics import get_aggregate_analytics
from .health import get_graphify_health
from .config_manager import (
    load_claude_settings,
    save_claude_settings,
    load_gemini_settings,
    save_gemini_settings,
    load_codex_settings,
    update_toml_value,
    get_targets_state,
    list_agents,
    list_skills,
    parse_markdown_frontmatter,
)
from .mcp_manager import (
    get_all_mcp_servers,
    load_disabled,
    save_disabled,
    get_mcp_servers,
    save_mcp_configs,
)

class ConfigHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to suppress standard HTTP logging to keep console clean
        pass

    def validate_host_and_origin(self, check_origin=True):
        host = self.headers.get("Host", "")
        # Allow localhost and 127.0.0.1 with any port or without port
        host_name = host.split(":")[0] if ":" in host else host
        if host_name not in ("localhost", "127.0.0.1"):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Bad Request: Invalid Host Header")
            return False

        if check_origin:
            origin = self.headers.get("Origin")
            referer = self.headers.get("Referer")
            
            if origin:
                parsed_origin = urllib.parse.urlparse(origin)
                origin_host = parsed_origin.hostname
                if origin_host not in ("localhost", "127.0.0.1"):
                    self.send_response(403)
                    self.end_headers()
                    self.wfile.write(b"Forbidden: Cross-Origin request blocked")
                    return False
                    
            if referer:
                parsed_referer = urllib.parse.urlparse(referer)
                referer_host = parsed_referer.hostname
                if referer_host and referer_host not in ("localhost", "127.0.0.1"):
                    self.send_response(403)
                    self.end_headers()
                    self.wfile.write(b"Forbidden: Cross-Origin referer blocked")
                    return False
        return True

    def do_GET(self):
        if not self.validate_host_and_origin(check_origin=False):
            return
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)
        
        # Serve transcript screenshots/media if requested
        unquoted_path = urllib.parse.unquote(path).strip("/")
        if any(x in unquoted_path for x in (".playwright-mcp", ".gemini", ".claude", ".codex")):
            if unquoted_path.startswith("home/"):
                file_path = Path("/") / unquoted_path
            else:
                file_path = Path.home() / unquoted_path
                if not file_path.exists():
                    file_path = REPO_DIR / unquoted_path

            if file_path.exists() and file_path.is_file():
                content_type = "image/png" if file_path.suffix == ".png" else "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(file_path.stat().st_size))
                self.end_headers()
                self.wfile.write(file_path.read_bytes())
                return
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"File not found")
                return
        
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
            
        # SPA Fallback: Serve index.html for any non-API routes that don't map to a static file
        if not path.startswith("/api/") and dist_dir.exists() and (dist_dir / "index.html").exists():
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write((dist_dir / "index.html").read_bytes())
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
                    "skills": list_skills(),
                    "graphify_health": get_graphify_health()
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
                
        elif path == "/api/conversations":
            try:
                conversations = get_all_conversations()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(conversations, indent=2).encode("utf-8"))
            except Exception as e:
                self.send_error_json(500, str(e))
                
        elif path == "/api/graphify/view":
            try:
                project_name = query.get("project", ["mswcc-front-fe"])[0]
                view_type = query.get("type", ["graph"])[0] # 'graph' or 'tree'
                
                # Find the project directory dynamically
                project_dir = None
                search_paths = [
                    Path.home() / "projects" / "company" / project_name,
                    Path.home() / "projects" / "personals" / project_name,
                    Path.home() / "projects" / project_name
                ]
                for p in search_paths:
                    if p.exists() and p.is_dir():
                        project_dir = p
                        break
                        
                if not project_dir:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(f"Project '{project_name}' not found".encode("utf-8"))
                    return
                    
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
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(f"Graph visualization file '{filename}' not found in project '{project_name}'".encode("utf-8"))
                    return
                    
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(file_path.stat().st_size))
                self.end_headers()
                self.wfile.write(file_path.read_bytes())
            except Exception as e:
                self.send_error_json(500, str(e))
                
        elif path == "/api/analytics":
            try:
                analytics = get_aggregate_analytics()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(analytics, indent=2).encode("utf-8"))
            except Exception as e:
                self.send_error_json(500, str(e))
                
        elif path == "/api/graphify/health":
            try:
                health = get_graphify_health()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(health, indent=2).encode("utf-8"))
            except Exception as e:
                self.send_error_json(500, str(e))
                
        elif path.startswith("/api/conversation/"):
            conv_id = path.replace("/api/conversation/", "")
            try:
                self.handle_get_conversation(conv_id)
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

    def handle_get_conversation(self, conv_id):
        clean_id = "".join(c for c in conv_id if c.isalnum() or c in "-_")
        parts = clean_id.split("__")
        if len(parts) < 2:
            self.send_error_json(400, "Invalid conversation ID format")
            return
            
        source = parts[0]
        steps = []
        model_name = "unknown"
        
        if source == "gemini":
            gemini_id = parts[1]
            log_file = BRAIN_DIR / gemini_id / ".system_generated" / "logs" / "transcript.jsonl"
            if not log_file.exists():
                self.send_error_json(404, "Gemini conversation log not found")
                return
            steps = parse_gemini_jsonl(log_file)
            model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
            
        elif source == "claude":
            if len(parts) < 3:
                self.send_error_json(400, "Invalid Claude conversation ID format")
                return
            project_dir_name = parts[1]
            session_id = parts[2]
            log_file = CLAUDE_DIR / project_dir_name / f"{session_id}.jsonl"
            if not log_file.exists():
                self.send_error_json(404, "Claude conversation log not found")
                return
            steps = parse_claude_jsonl(log_file)
            model_name = "claude-3-5-sonnet"
            try:
                with log_file.open("r", encoding="utf-8") as f:
                    for line in f:
                        data = json.loads(line)
                        if data.get("type") == "assistant" and "message" in data:
                            model_name = data["message"].get("model", model_name)
                            break
            except Exception:
                pass
            
        elif source == "codex":
            if len(parts) < 3:
                self.send_error_json(400, "Invalid Codex conversation ID format")
                return
            year_month_day = parts[1]
            rollout_filename = parts[2]
            
            y_m_d_parts = year_month_day.split("-")
            if len(y_m_d_parts) != 3:
                self.send_error_json(400, "Invalid Codex date format")
                return
            year, month, day = y_m_d_parts
            
            log_file = CODEX_DIR / year / month / day / f"{rollout_filename}.jsonl"
            if not log_file.exists():
                self.send_error_json(404, "Codex conversation log not found")
                return
            steps = parse_codex_jsonl(log_file)
            model_name = "gpt-5"
            try:
                with log_file.open("r", encoding="utf-8") as f:
                    for line in f:
                        data = json.loads(line)
                        if data.get("type") == "session_meta" and "payload" in data:
                            model_name = data["payload"].get("model_provider", model_name)
                            break
            except Exception:
                pass
        else:
            self.send_error_json(400, f"Unsupported conversation source: {source}")
            return

        # Determine model rates
        model_lower = model_name.lower()
        if "pro" in model_lower:
            input_rate = 1.25
            output_rate = 5.00
        elif "flash" in model_lower:
            input_rate = 0.075
            output_rate = 0.30
        elif "sonnet" in model_lower or "claude-3-5" in model_lower or "claude-3.7" in model_lower:
            input_rate = 3.00
            output_rate = 15.00
        elif "opus" in model_lower:
            input_rate = 15.00
            output_rate = 75.00
        elif "haiku" in model_lower:
            input_rate = 0.25
            output_rate = 1.25
        elif "gpt-5" in model_lower or "openai" in model_lower:
            input_rate = 5.00
            output_rate = 15.00
        else:
            input_rate = 1.25
            output_rate = 5.00

        stats = {
            "total_steps": 0,
            "user_messages": 0,
            "tool_calls": 0,
            "est_input_tokens": 0,
            "est_output_tokens": 0,
            "est_cost": 0.0,
            "model_name": model_name,
            "input_rate": input_rate,
            "output_rate": output_rate
        }
        
        for step in steps:
            content = step.get("content")
            if content is None:
                content = ""
            step["content"] = content
            tokens = estimate_tokens(content)
            step["est_tokens"] = tokens
            
            stats["total_steps"] += 1
            step_type = step.get("type")
            if step_type == "USER_INPUT":
                stats["user_messages"] += 1
                stats["est_input_tokens"] += 25000 + tokens
            elif step_type == "PLANNER_RESPONSE":
                stats["est_output_tokens"] += tokens
            elif step_type in (
                "RUN_COMMAND", "VIEW_FILE", "GREP_SEARCH", "LIST_DIRECTORY",
                "MCP_TOOL", "CODE_ACTION", "SEARCH_WEB", "READ_URL_CONTENT",
                "ASK_QUESTION", "INVOKE_SUBAGENT", "CHECKPOINT", "ERROR_MESSAGE",
                "LIST_RESOURCES", "GENERIC"
            ):
                if step_type != "CHECKPOINT":
                    stats["tool_calls"] += 1
                stats["est_input_tokens"] += tokens

        input_cost = (stats["est_input_tokens"] / 1_000_000.0) * input_rate
        output_cost = (stats["est_output_tokens"] / 1_000_000.0) * output_rate
        stats["est_cost"] = round(input_cost + output_cost, 4)
        
        payload = {
            "id": clean_id,
            "stats": stats,
            "steps": steps
        }
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))

    def do_POST(self):
        if not self.validate_host_and_origin(check_origin=True):
            return
            
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        if path.startswith("/api/"):
            content_type = self.headers.get("Content-Type", "")
            if not content_type.split(";")[0].strip().lower() == "application/json":
                self.send_response(415)
                self.end_headers()
                self.wfile.write(b"Unsupported Media Type: Content-Type must be application/json")
                return
        
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
        elif path == "/api/graphify/update":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                project_name = payload.get("project", "mswcc-front-fe")
                force = payload.get("force", False)
                
                # Find project directory dynamically
                project_dir = None
                search_paths = [
                    Path.home() / "projects" / "company" / project_name,
                    Path.home() / "projects" / "personals" / project_name,
                    Path.home() / "projects" / project_name
                ]
                for p in search_paths:
                    if p.exists() and p.is_dir():
                        project_dir = p
                        break
                        
                if not project_dir:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(f"Project '{project_name}' not found".encode("utf-8"))
                    return
                
                # Run graphify update
                cmd = ["graphify", "update", "."]
                if force:
                    cmd.append("--force")
                
                result = subprocess.run(cmd, cwd=str(project_dir), capture_output=True, text=True)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success" if result.returncode == 0 else "error",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }).encode("utf-8"))
            except Exception as e:
                self.send_error_json(500, str(e))
        elif path == "/api/graphify/rebuild":
            try:
                # Run graphify update on current config repo
                cmd = ["graphify", "update", "."]
                result = subprocess.run(cmd, cwd=str(REPO_DIR), capture_output=True, text=True)
                health = get_graphify_health()
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success" if result.returncode == 0 else "error",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "health": health
                }).encode("utf-8"))
            except Exception as e:
                self.send_error_json(500, str(e))
        elif path == "/api/simulator/execute":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                action = payload.get("action")
                args = payload.get("args", {})
                
                if action == "view_file":
                    file_path = args.get("AbsolutePath", "")
                    resolved_path = Path(file_path).resolve()
                    if not resolved_path.exists() or not resolved_path.is_file():
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "message": f"File '{file_path}' does not exist or is not a file."}).encode("utf-8"))
                        return
                    
                    try:
                        with open(resolved_path, "r", encoding="utf-8") as f:
                            lines = [f.readline() for _ in range(15)]
                            content = "".join(lines)
                            if f.readline():
                                content += "\n... (truncated)"
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "success", "output": content}).encode("utf-8"))
                    except Exception as e:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
                
                elif action == "run_command":
                    cmd_line = args.get("CommandLine", "")
                    if not cmd_line:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "message": "Command is empty."}).encode("utf-8"))
                        return
                    
                    try:
                        proc = subprocess.run(
                            cmd_line,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            timeout=5.0,
                            cwd=str(REPO_DIR)
                        )
                        stdout_str = proc.stdout.decode("utf-8", errors="replace")
                        stderr_str = proc.stderr.decode("utf-8", errors="replace")
                        output = stdout_str + stderr_str
                        
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "status": "success" if proc.returncode == 0 else "error",
                            "output": output or "[No output generated]"
                        }).encode("utf-8"))
                    except subprocess.TimeoutExpired:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "message": "Command execution timed out (5s limit)."}).encode("utf-8"))
                    except Exception as e:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
                else:
                    self.send_response(400)
                    self.end_headers()
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
