import sys
import subprocess
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .constants import REPO_DIR
from .health import get_graphify_health
from .analytics import get_aggregate_analytics
from .token_estimator import calculate_session_stats
from .utils import is_safe_path, verify_session_token

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
    read_simulator_file,
    execute_simulator_command,
    test_mcp_server,
)
from .mcp_manager import (
    get_mcp_servers,
    get_all_mcp_servers,
    load_disabled,
    save_disabled,
    save_mcp_configs,
)
from .metadata import (
    get_all_conversations,
    resolve_conversation_log,
    describe_gemini_transcript_source,
)
from .parsers import parse_gemini_jsonl, parse_claude_jsonl, parse_codex_jsonl

router = APIRouter(prefix="/api")

# --- Schemas ---

class SaveTempPayload(BaseModel):
    claude: dict = {}
    gemini: dict = {}
    codex: dict = {}
    disabled_mcp: list = []
    gemini_instructions: str = ""
    claude_instructions: str = ""
    codex_instructions: str = ""
    mcp_servers: dict = {}

class GraphifyUpdatePayload(BaseModel):
    project: str = "mswcc-front-fe"
    force: bool = False

class SimulatorExecutePayload(BaseModel):
    action: str
    args: dict = {}

# --- GET Routes ---

@router.get("/config")
def get_config():
    try:
        return {
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agent/{name}")
def get_agent(name: str):
    from .constants import AGENTS_DIR
    agent_file = AGENTS_DIR / f"{name}.md"
    if not agent_file.exists():
        raise HTTPException(status_code=404, detail="Agent not found")
    try:
        res = load_markdown_content(agent_file)
        res["name"] = name
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/skill/{name}")
def get_skill(name: str):
    from .constants import SKILLS_DIR
    skill_file = SKILLS_DIR / name / "SKILL.md"
    if not skill_file.exists():
        raise HTTPException(status_code=404, detail="Skill not found")
    try:
        res = load_markdown_content(skill_file)
        res["name"] = name
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations")
def get_conversations():
    try:
        return get_all_conversations()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversation/{conv_id}")
def get_conversation(conv_id: str):
    clean_id = "".join(c for c in conv_id if c.isalnum() or c in "-_")
    parts = clean_id.split("__")
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")
        
    source = parts[0]
    if source not in ("gemini", "claude", "codex"):
        raise HTTPException(status_code=400, detail=f"Unsupported conversation source: {source}")
        
    if source == "claude" and len(parts) < 3:
        raise HTTPException(status_code=400, detail="Invalid Claude conversation ID format")
        
    if source == "codex":
        if len(parts) < 3:
            raise HTTPException(status_code=400, detail="Invalid Codex conversation ID format")
        year_month_day = parts[1]
        if len(year_month_day.split("-")) != 3:
            raise HTTPException(status_code=400, detail="Invalid Codex date format")

    log_file, model_name = resolve_conversation_log(conv_id)
    if log_file is None or not log_file.exists():
        source_cap = source.capitalize() if source != "gemini" else "Gemini"
        raise HTTPException(status_code=404, detail=f"{source_cap} conversation log not found")
        
    steps = []
    log_source = None
    
    if source == "gemini":
        log_source = describe_gemini_transcript_source(parts[1])
        steps = parse_gemini_jsonl(log_file)
    elif source == "claude":
        steps = parse_claude_jsonl(log_file)
    elif source == "codex":
        steps = parse_codex_jsonl(log_file)

    stats = calculate_session_stats(steps, model_name)
    
    payload = {
        "id": clean_id,
        "stats": stats,
        "steps": steps
    }
    if log_source is not None:
        payload["log_source"] = log_source
    return payload

@router.get("/graphify/view")
def get_graphify_view(
    project: str = "mswcc-front-fe",
    type: str = "graph"
):
    from fastapi.responses import HTMLResponse
    project_dir = resolve_project_dir(project)
    if not project_dir:
        raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
        
    file_path, err_msg = generate_graphify_view(project_dir, type, project)
    if err_msg:
        raise HTTPException(status_code=404, detail=err_msg)
        
    return HTMLResponse(content=file_path.read_bytes())

@router.get("/analytics")
def get_analytics():
    try:
        return get_aggregate_analytics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/graphify/health")
def get_graphify_health_route():
    try:
        return get_graphify_health()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/apply/stream")
def get_apply_stream(
    force: bool = False,
    claude: bool = True,
    codex: bool = True,
    agy: bool = True
):
    def event_generator():
        def sse_line(data: str):
            return f"data: {data}\n\n"

        yield sse_line("🚀 Starting installation process...")
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
            
        yield sse_line(f"Command: {' '.join(args)}")
        try:
            p = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in iter(p.stdout.readline, ""):
                yield sse_line(line.rstrip())
            p.wait()
            if p.returncode == 0:
                yield sse_line("SUCCESS: ✓ Done! All changes saved and applied successfully.")
            else:
                yield sse_line(f"ERROR: ✘ Apply failed with exit code {p.returncode}. Changes remain staged.")
        except Exception as e:
            yield sse_line(f"ERROR: ✘ Error running installer: {e}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- POST Routes ---

@router.post("/save-temp")
def post_save_temp(payload: SaveTempPayload):
    try:
        # 1. Save Claude
        save_claude_settings(payload.claude)

        # 1.5. Save Gemini
        save_gemini_settings(payload.gemini)

        # 2. Save Codex
        template_path = REPO_DIR / "codex" / "config.toml"
        codex_data = payload.codex
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
        save_disabled(payload.disabled_mcp)

        # 4. Save Gemini, Claude, and Codex instructions
        (REPO_DIR / "gemini" / "ANTIGRAVITY.md").write_text(payload.gemini_instructions)
        (REPO_DIR / "claude" / "CLAUDE.md").write_text(payload.claude_instructions)
        (REPO_DIR / "codex" / "AGENTS.md").write_text(payload.codex_instructions)

        # 5. Save MCP configurations directly to ~/.claude.json
        save_mcp_configs(payload.mcp_servers, payload.disabled_mcp)

        return {"status": "success", "message": "Settings saved to templates"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/graphify/update")
def post_graphify_update(payload: GraphifyUpdatePayload):
    try:
        project_dir = resolve_project_dir(payload.project)
        if not project_dir:
            raise HTTPException(status_code=404, detail=f"Project '{payload.project}' not found")
        
        return run_graphify_update(project_dir, payload.force)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/graphify/rebuild")
def post_graphify_rebuild():
    try:
        res = run_graphify_update(REPO_DIR, force=False)
        res["health"] = get_graphify_health()
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/simulator/execute")
def post_simulator_execute(
    payload: SimulatorExecutePayload,
    _ = Depends(verify_session_token)
):
    try:
        if payload.action == "view_file":
            file_path = payload.args.get("AbsolutePath", "")
            return read_simulator_file(Path(file_path))
        elif payload.action == "run_command":
            cmd_line = payload.args.get("CommandLine", "")
            if not cmd_line:
                return {"status": "error", "message": "Command is empty."}
            return execute_simulator_command(cmd_line, REPO_DIR)
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/mcp/test")
def post_mcp_test(payload: dict):
    try:
        return test_mcp_server(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
