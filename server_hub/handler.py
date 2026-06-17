import json
import subprocess
import sys
import urllib.parse
import os
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from .constants import REPO_DIR, BRAIN_DIR, CLAUDE_DIR, CODEX_DIR, AGENTS_DIR, SKILLS_DIR
from .parsers import parse_gemini_jsonl, parse_claude_jsonl, parse_codex_jsonl
from .metadata import (
    get_all_conversations,
    resolve_gemini_transcript_path,
    describe_gemini_transcript_source,
)
from .token_estimator import calculate_session_stats
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
    load_markdown_content,
)
from .system_ops import (
    resolve_project_dir,
    generate_graphify_view,
    run_graphify_update,
    execute_simulator_command,
    read_simulator_file,
    test_mcp_server,
)
from .mcp_manager import (
    get_all_mcp_servers,
    load_disabled,
    save_disabled,
    get_mcp_servers,
    save_mcp_configs,
)



def is_safe_path(requested_path, allowed_bases):
    try:
        resolved_path = Path(requested_path).resolve()
        for base in allowed_bases:
            resolved_base = Path(base).resolve()
            if resolved_base in resolved_path.parents or resolved_base == resolved_path:
                return True
        return False
    except Exception:
        return False

class ConfigHandler(BaseHTTPRequestHandler):
    session_token = None

    def log_message(self, format, *args):
        # Override to suppress standard HTTP logging to keep console clean
        pass

    def validate_host_and_origin(self, check_origin=True):
        host = self.headers.get("Host", "")
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

    def verify_session_token(self):
        # If no session token is configured, skip verification
        if not getattr(self, "session_token", None):
            return True
            
        # 1. Check X-Session-Token header
        x_token = self.headers.get("X-Session-Token")
        if x_token and x_token == self.session_token:
            return True
            
        # 2. Check Authorization header (Bearer token)
        auth_header = self.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            bearer_token = auth_header[7:].strip()
            if bearer_token == self.session_token:
                return True
                
        # 3. Check Cookie header
        cookie_header = self.headers.get("Cookie")
        if cookie_header:
            from http.cookies import SimpleCookie
            try:
                cookie = SimpleCookie()
                cookie.load(cookie_header)
                if "session_token" in cookie and cookie["session_token"].value == self.session_token:
                    return True
            except Exception:
                pass
                
        return False

    def do_GET(self):
        if not self.validate_host_and_origin(check_origin=False):
            return
            
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)
        
        # 1. Handle API Endpoints
        if path.startswith("/api/"):
            if path == "/api/config":
                self._handle_api_config()
            elif path.startswith("/api/agent/"):
                name = path.replace("/api/agent/", "")
                self._handle_api_agent(name)
            elif path.startswith("/api/skill/"):
                name = path.replace("/api/skill/", "")
                self._handle_api_skill(name)
            elif path == "/api/conversations":
                self._handle_api_conversations()
            elif path == "/api/graphify/view":
                self._handle_api_graphify_view(query)
            elif path == "/api/analytics":
                self._handle_api_analytics()
            elif path == "/api/graphify/health":
                self._handle_api_graphify_health()
            elif path.startswith("/api/conversation/"):
                conv_id = path.replace("/api/conversation/", "")
                self._handle_api_conversation(conv_id)
            elif path == "/api/apply/stream":
                self._handle_api_apply_stream(query)
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"API Endpoint Not Found")
            return

        # 2. Serve Static Resources (screenshots/media, Vite React app, or Root fallback)
        self._serve_static_resources(path)

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
                
        # Parse JSON body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            payload = json.loads(body) if body else {}
        except Exception as e:
            self.send_error_json(400, f"Invalid JSON payload: {e}")
            return

        # POST Route Dispatching
        if path == "/api/save-temp":
            self._handle_post_save_temp(payload)
        elif path == "/api/graphify/update":
            self._handle_post_graphify_update(payload)
        elif path == "/api/graphify/rebuild":
            self._handle_post_graphify_rebuild()
        elif path == "/api/simulator/execute":
            if not self.verify_session_token():
                self.send_error_json(401, "Unauthorized: Invalid or missing session token")
                return
            self._handle_post_simulator_execute(payload)
        elif path == "/api/mcp/test":
            self._handle_post_mcp_test(payload)
        else:
            self.send_response(404)
            self.end_headers()

    # --- GET API Route Handlers ---

    def _handle_api_config(self):
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
            self.send_json(200, config_data)
        except Exception as e:
            self.send_error_json(500, str(e))

    def _handle_api_agent(self, name):
        agent_file = AGENTS_DIR / f"{name}.md"
        if not agent_file.exists():
            self.send_error_json(404, "Agent not found")
            return
        try:
            res = load_markdown_content(agent_file)
            res["name"] = name
            self.send_json(200, res)
        except Exception as e:
            self.send_error_json(500, str(e))

    def _handle_api_skill(self, name):
        skill_file = SKILLS_DIR / name / "SKILL.md"
        if not skill_file.exists():
            self.send_error_json(404, "Skill not found")
            return
        try:
            res = load_markdown_content(skill_file)
            res["name"] = name
            self.send_json(200, res)
        except Exception as e:
            self.send_error_json(500, str(e))

    def _handle_api_conversations(self):
        try:
            conversations = get_all_conversations()
            self.send_json(200, conversations)
        except Exception as e:
            self.send_error_json(500, str(e))

    def _handle_api_graphify_view(self, query):
        try:
            project_name = query.get("project", ["mswcc-front-fe"])[0]
            view_type = query.get("type", ["graph"])[0]  # 'graph', 'tree', or 'callflow'
            
            project_dir = resolve_project_dir(project_name)
            if not project_dir:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(f"Project '{project_name}' not found".encode("utf-8"))
                return
                
            file_path, err_msg = generate_graphify_view(project_dir, view_type, project_name)
            if err_msg:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(err_msg.encode("utf-8"))
                return
                
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(file_path.stat().st_size))
            self.end_headers()
            self.wfile.write(file_path.read_bytes())
        except Exception as e:
            self.send_error_json(500, str(e))

    def _handle_api_analytics(self):
        try:
            analytics = get_aggregate_analytics()
            self.send_json(200, analytics)
        except Exception as e:
            self.send_error_json(500, str(e))

    def _handle_api_graphify_health(self):
        try:
            health = get_graphify_health()
            self.send_json(200, health)
        except Exception as e:
            self.send_error_json(500, str(e))

    def _handle_api_conversation(self, conv_id):
        try:
            self.handle_get_conversation(conv_id)
        except Exception as e:
            self.send_error_json(500, str(e))

    def _handle_api_apply_stream(self, query):
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
        if agy: targets.append("--gemini")
        
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

    # --- POST API Route Handlers ---

    def _handle_post_save_temp(self, payload):
        try:
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

            self.send_json(200, {"status": "success", "message": "Settings saved to templates"})
        except Exception as e:
            self.send_error_json(500, str(e))

    def _handle_post_graphify_update(self, payload):
        try:
            project_name = payload.get("project", "mswcc-front-fe")
            force = payload.get("force", False)
            
            project_dir = resolve_project_dir(project_name)
            if not project_dir:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(f"Project '{project_name}' not found".encode("utf-8"))
                return
            
            res = run_graphify_update(project_dir, force)
            self.send_json(200, res)
        except Exception as e:
            self.send_error_json(500, str(e))

    def _handle_post_graphify_rebuild(self):
        try:
            res = run_graphify_update(REPO_DIR, force=False)
            res["health"] = get_graphify_health()
            self.send_json(200, res)
        except Exception as e:
            self.send_error_json(500, str(e))

    def _handle_post_simulator_execute(self, payload):
        try:
            action = payload.get("action")
            args = payload.get("args", {})
            
            if action == "view_file":
                file_path = args.get("AbsolutePath", "")
                res = read_simulator_file(Path(file_path))
                self.send_json(200, res)
            elif action == "run_command":
                cmd_line = args.get("CommandLine", "")
                if not cmd_line:
                    self.send_json(200, {"status": "error", "message": "Command is empty."})
                    return
                res = execute_simulator_command(cmd_line, REPO_DIR)
                self.send_json(200, res)
            else:
                self.send_response(400)
                self.end_headers()
        except Exception as e:
            self.send_error_json(500, str(e))

    def _handle_post_mcp_test(self, payload):
        try:
            res = test_mcp_server(payload)
            self.send_json(200, res)
        except Exception as e:
            self.send_error_json(500, str(e))

    # --- Static File Serving Helper ---

    def _serve_static_resources(self, path):
        # 1. Check for transcript screenshots/media (e.g. .gemini, .claude, etc.)
        unquoted_path = urllib.parse.unquote(path).strip("/")
        if any(x in unquoted_path for x in (".playwright-mcp", ".gemini", ".claude", ".codex")):
            file_path = Path("/") / unquoted_path if unquoted_path.startswith("home/") else Path.home() / unquoted_path
            if not file_path.exists():
                file_path = REPO_DIR / unquoted_path

            # Enforce path safety checks
            allowed_bases = [
                REPO_DIR,
                Path.home() / ".gemini",
                Path.home() / ".claude",
                Path.home() / ".codex",
                Path.home() / ".playwright-mcp"
            ]
            if not is_safe_path(file_path, allowed_bases):
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden: Path is outside of allowed directories")
                return

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

        # 2. Serve static files from compiled Vite React app (frontend/dist/)
        dist_dir = REPO_DIR / "frontend" / "dist"
        rel_path = path.lstrip("/")
        file_to_serve = dist_dir / "index.html" if not rel_path or rel_path == "index.html" else dist_dir / rel_path
        
        if dist_dir.exists() and file_to_serve.exists() and file_to_serve.is_file() and dist_dir in file_to_serve.resolve().parents:
            self.send_response(200)
            if file_to_serve.suffix == ".html":
                self.send_header("Content-Type", "text/html")
                if getattr(self, "session_token", None):
                    self.send_header("Set-Cookie", f"session_token={self.session_token}; Path=/; HttpOnly; SameSite=Strict")
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
            
        # 3. SPA Fallback: Serve dist/index.html for routing
        if not path.startswith("/api/") and dist_dir.exists() and (dist_dir / "index.html").exists():
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            if getattr(self, "session_token", None):
                self.send_header("Set-Cookie", f"session_token={self.session_token}; Path=/; HttpOnly; SameSite=Strict")
            self.end_headers()
            self.wfile.write((dist_dir / "index.html").read_bytes())
            return
            
        # 4. Fallback to repository root index.html if dist doesn't exist and path is root
        if (path == "/" or path == "/index.html") and not dist_dir.exists():
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            if getattr(self, "session_token", None):
                self.send_header("Set-Cookie", f"session_token={self.session_token}; Path=/; HttpOnly; SameSite=Strict")
            self.end_headers()
            self.wfile.write((REPO_DIR / "index.html").read_bytes())
            return

        # 5. Default Not Found
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")

    # --- Core Log Parsing Method (Dependent for Tests) ---

    def handle_get_conversation(self, conv_id):
        clean_id = "".join(c for c in conv_id if c.isalnum() or c in "-_")
        parts = clean_id.split("__")
        if len(parts) < 2:
            self.send_error_json(400, "Invalid conversation ID format")
            return
            
        source = parts[0]
        steps = []
        model_name = "unknown"
        log_source = None
        
        if source == "gemini":
            gemini_id = parts[1]
            log_file = resolve_gemini_transcript_path(gemini_id)
            if log_file is None:
                self.send_error_json(404, "Gemini conversation log not found")
                return
            log_source = describe_gemini_transcript_source(gemini_id)
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

        stats = calculate_session_stats(steps, model_name)
        
        payload = {
            "id": clean_id,
            "stats": stats,
            "steps": steps
        }
        if log_source is not None:
            payload["log_source"] = log_source
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    # --- Core SSE and JSON Helper Methods ---

    def send_sse_line(self, data: str):
        try:
            self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
            self.wfile.flush()
        except (ConnectionResetError, BrokenPipeError):
            pass

    def send_json(self, status_code: int, data: dict):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def send_error_json(self, code: int, message: str):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"detail": message}).encode("utf-8"))
