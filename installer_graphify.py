"""Graphify hook policy and project-level config merging."""

import json
import os
import shlex
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path


MANAGED_GRAPHIFY_MARKER = "ai-coding-config:graphify-managed"
BROAD_DISCOVERY_COMMANDS = {"grep", "rg", "ripgrep", "find", "fd", "ack", "ag"}
SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb",
    ".c", ".h", ".cpp", ".hpp", ".cc", ".cs", ".kt", ".swift", ".php",
    ".scala", ".lua", ".sh", ".md", ".rst", ".txt", ".mdx",
}
IGNORED_SOURCE_PARTS = {
    "graphify-out", "skills", ".claude", ".gemini", ".codex", ".git", "node_modules",
}
GRAPHIFY_GUIDANCE = (
    "This project has a knowledge graph at graphify-out/. For architecture or broad "
    "codebase discovery, the FIRST tool call must be `rtk graphify query \"<question>\"`; "
    "do not run ls/which/test or read source first. Use at most 3 Graphify calls total: "
    "the initial query plus at most 2 follow-up query/path/explain calls, then hard stop "
    "all Graphify calls and synthesize the answer. Read "
    "GRAPH_REPORT.md only when scoped Graphify results are insufficient or the user asks "
    "for a broad report. Targeted raw reads are allowed for specific edits and debugging."
)
GRAPHIFY_INSTRUCTIONS = f"""## graphify

{GRAPHIFY_GUIDANCE}

Rules:
- For an architecture question, the FIRST tool call must be one broad `rtk graphify query "<question>"`. Do not check Graphify with `ls`, `which`, or `test` first.
- Use at most 3 Graphify calls total: the initial query plus at most 2 follow-up `query`, `path`, or `explain` calls. After the third call, hard stop all Graphify calls and synthesize the answer from available context.
- Dirty `graphify-out/` files are expected after hooks or incremental updates and are not a reason to skip Graphify.
- If `graphify-out/wiki/index.md` exists, use it for broad navigation instead of raw source browsing.
- Read `graphify-out/GRAPH_REPORT.md` only when scoped queries are insufficient or the user requests a broad report.
- After Graphify discovery, targeted raw reads are allowed for editing or debugging specific code.
- After modifying code, run `graphify update .`.
"""
INSTRUCTION_START = "<!-- ai-coding-config:graphify-start -->"
INSTRUCTION_END = "<!-- ai-coding-config:graphify-end -->"
PROJECT_GRAPHIFY_BLOCK = f"{INSTRUCTION_START}\n{GRAPHIFY_INSTRUCTIONS.rstrip()}\n{INSTRUCTION_END}"


def _command_words(command: str) -> list[str]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars="|&;()")
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return []

    executables = []
    expect_command = True
    wrappers = {"rtk", "sudo", "command", "builtin", "env", "nohup"}
    for token in tokens:
        if token in {"|", "||", "&&", ";", "(", ")", "&"}:
            expect_command = True
            continue
        if not expect_command or "=" in token and not token.startswith(("/", "./")):
            continue
        executable = Path(token).name
        if executable in wrappers:
            continue
        executables.append(executable)
        expect_command = False
    return executables


def is_broad_discovery_command(command: str) -> bool:
    return any(word in BROAD_DISCOVERY_COMMANDS for word in _command_words(command))


def is_graphify_probe_command(command: str) -> bool:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    words = [Path(token).name.lower() for token in tokens]
    normalized = command.lower().replace("\\", "/")
    probes_graph_file = "graphify-out/graph.json" in normalized and any(
        word in {"test", "[", "ls", "stat"} for word in words
    )
    return probes_graph_file


def is_source_tool_input(tool_input: dict) -> bool:
    for raw_path in (
        tool_input.get("file_path"), tool_input.get("path"), tool_input.get("pattern")
    ):
        if not raw_path:
            continue
        normalized = str(raw_path).lower().replace("\\", "/")
        if set(Path(normalized).parts) & IGNORED_SOURCE_PARTS:
            continue
        if Path(normalized).suffix in SOURCE_EXTENSIONS:
            return True
    return False


def classify_graphify_tool_use(tool_name: str, tool_input: dict, graph_exists: bool) -> dict:
    result = {"decision": "allow"}
    if not graph_exists:
        return result
    if tool_name.lower() == "grep":
        return {
            "decision": "deny",
            "additionalContext": f"BLOCKED by graphify hook: {GRAPHIFY_GUIDANCE}",
        }
    if tool_name.lower() == "bash":
        command = str(tool_input.get("command", ""))
        if is_graphify_probe_command(command):
            return {"decision": "allow"}
        if is_broad_discovery_command(command):
            return {
                "decision": "deny",
                "additionalContext": f"BLOCKED by graphify hook: {GRAPHIFY_GUIDANCE}",
            }
    if tool_name.lower() in {"read", "glob", "read_file", "list_directory"} and is_source_tool_input(tool_input):
        result["additionalContext"] = GRAPHIFY_GUIDANCE
    return result


def _hook_classifier_script(tool_name: str, claude: bool) -> str:
    constants = (
        f"B={tuple(sorted(BROAD_DISCOVERY_COMMANDS))!r};"
        f"E={tuple(sorted(SOURCE_EXTENSIONS))!r};"
        f"I={tuple(sorted(IGNORED_SOURCE_PARTS))!r};"
        f"G={GRAPHIFY_GUIDANCE!r};"
    )
    logic = r'''import json,pathlib,shlex,sys,tempfile
data=json.load(sys.stdin); t=data.get("tool_input",data); decision="allow"; context=None;session=str(data.get("session_id") or "")
exists=pathlib.Path("graphify-out/graph.json").exists()
if exists and TOOL=="Grep":
 decision="deny";context="BLOCKED by graphify hook: "+G
elif exists and TOOL=="Bash":
 raw=str(t.get("command", ""));low=raw.lower().replace(chr(92),"/")
 try:
  lx=shlex.shlex(raw,posix=True,punctuation_chars="|&;()");lx.whitespace_split=True;tokens=list(lx)
 except ValueError: tokens=[]
 ex=[];expect=True
 for token in tokens:
  if token in {"|","||","&&",";","(",")","&"}: expect=True;continue
  if not expect or ("=" in token and not token.startswith(("/","./"))): continue
  word=pathlib.Path(token).name
  if word in {"rtk","sudo","command","builtin","env","nohup"}: continue
  ex.append(word);expect=False
 words=[pathlib.Path(token).name.lower() for token in tokens]
 probe=("graphify-out/graph.json" in low and any(word in {"test","[","ls","stat"} for word in words))
 graph_call="graphify" in ex and any(("graphify "+sub) in low for sub in ("query","path","explain"))
 over_quota=False
 if graph_call and session:
  safe="".join(ch for ch in session if ch.isalnum() or ch in "-_")[:120]
  state=pathlib.Path(tempfile.gettempdir())/("ai-coding-config-graphify-"+safe+".count")
  with state.open("a+") as handle:
   try:
    import fcntl;fcntl.flock(handle,fcntl.LOCK_EX)
   except (ImportError,AttributeError,PermissionError,OSError):
    try:import msvcrt;msvcrt.locking(handle.fileno(),1,1)
    except (ImportError,PermissionError,OSError):pass
   handle.seek(0)
   try: count=int(handle.read().strip() or "0")
   except ValueError: count=0
   over_quota=count>=3
   if not over_quota:
    handle.seek(0);handle.truncate();handle.write(str(count+1));handle.flush()
   try:
    import fcntl;fcntl.flock(handle,fcntl.LOCK_UN)
   except (ImportError,AttributeError,PermissionError,OSError):
    try:import msvcrt;msvcrt.locking(handle.fileno(),0,1)
    except (ImportError,PermissionError,OSError):pass
 if over_quota: decision="deny";context="BLOCKED by graphify hook: Maximum 3 Graphify discovery calls reached for this session. Synthesize the answer from available context."
 elif any(word in B for word in ex): decision="deny";context="BLOCKED by graphify hook: "+G
elif exists:
 values=[t.get("file_path"),t.get("path"),t.get("pattern")]
 for value in values:
  if not value: continue
  p=str(value).lower().replace(chr(92),"/");parts=set(pathlib.Path(p).parts)
  if not parts.intersection(I) and pathlib.Path(p).suffix in E: context=G;break
'''
    if claude:
        output = r'''out={}
if context:
 out={"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":context}}
 if decision=="deny": out["hookSpecificOutput"].update({"permissionDecision":"deny","permissionDecisionReason":context})
sys.stdout.write(json.dumps(out) if out else "")
'''
    else:
        output = r'''out={"decision":decision}
if context: out["additionalContext"]=context
sys.stdout.write(json.dumps(out))
'''
    return constants + f"TOOL={tool_name!r};" + logic + output


def _python_hook_command(tool_name: str, claude: bool) -> str:
    script = _hook_classifier_script(tool_name, claude)
    # Claude Code uses bash on all platforms (including Windows via Git Bash).
    # Use # comment and shlex.quote (bash-compatible). On Windows, python3
    # may not exist in PATH — use "python" instead.
    py = "python3" if sys.platform != "win32" else "python"
    return f"# {MANAGED_GRAPHIFY_MARKER}\n{py} -c {shlex.quote(script)}"


def managed_claude_hooks() -> list[dict]:
    return [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": _python_hook_command("Bash", True)}]},
        {"matcher": "Grep", "hooks": [{"type": "command", "command": _python_hook_command("Grep", True)}]},
        {"matcher": "Read|Glob", "hooks": [{"type": "command", "command": _python_hook_command("Read", True)}]},
    ]


def managed_gemini_hooks() -> list[dict]:
    return [
        {"matcher": "run_shell_command", "hooks": [{"type": "command", "command": _python_hook_command("Bash", False)}]},
        {"matcher": "read_file|list_directory", "hooks": [{"type": "command", "command": _python_hook_command("Read", False)}]},
    ]


def managed_codex_hooks() -> list[dict]:
    return [{
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": f"# {MANAGED_GRAPHIFY_MARKER}\ngraphify hook-check"}],
    }]


def is_managed_graphify_hook(hook: dict) -> bool:
    legacy_signatures = (
        "BLOCKED by graphify hook:",
        "graphify: knowledge graph at graphify-out/",
        "graphify hook-check",
    )
    return any(
        MANAGED_GRAPHIFY_MARKER in str(item.get("command", ""))
        or any(signature in str(item.get("command", "")) for signature in legacy_signatures)
        for item in hook.get("hooks", [])
        if isinstance(item, dict)
    )


def _backup_path(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = path.with_name(f"{path.name}.backup-{stamp}")
    shutil.move(str(path), str(backup))
    return backup


def _load_json_for_merge(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        _backup_path(path)
        return {}


def _merge_managed_hooks(path: Path, event: str, managed_hooks: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    settings = _load_json_for_merge(path)
    hooks = settings.setdefault("hooks", {})
    existing = hooks.get(event, [])
    if not isinstance(existing, list):
        existing = []
    hooks[event] = [h for h in existing if not is_managed_graphify_hook(h)] + managed_hooks
    path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


def _merge_project_instructions(path: Path) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if INSTRUCTION_START in existing and INSTRUCTION_END in existing:
        before, remainder = existing.split(INSTRUCTION_START, 1)
        _, after = remainder.split(INSTRUCTION_END, 1)
        merged = before.rstrip() + "\n\n" + PROJECT_GRAPHIFY_BLOCK + after
    else:
        merged = existing.rstrip() + ("\n\n" if existing.strip() else "") + PROJECT_GRAPHIFY_BLOCK + "\n"
    path.write_text(merged, encoding="utf-8")


def configure_claude_project(project_dir: Path) -> None:
    _merge_managed_hooks(project_dir / ".claude" / "settings.json", "PreToolUse", managed_claude_hooks())
    if (project_dir / "graphify-out" / "graph.json").exists():
        _merge_project_instructions(project_dir / "CLAUDE.md")


def configure_gemini_project(project_dir: Path) -> None:
    _merge_managed_hooks(project_dir / ".gemini" / "settings.json", "BeforeTool", managed_gemini_hooks())
    if (project_dir / "graphify-out" / "graph.json").exists():
        _merge_project_instructions(project_dir / "ANTIGRAVITY.md")


def configure_codex_project(project_dir: Path) -> None:
    codex_dir = project_dir / ".codex"
    if codex_dir.exists() and not codex_dir.is_dir():
        _backup_path(codex_dir)
    codex_dir.mkdir(parents=True, exist_ok=True)
    _merge_managed_hooks(codex_dir / "hooks.json", "PreToolUse", managed_codex_hooks())
    if (project_dir / "graphify-out" / "graph.json").exists():
        _merge_project_instructions(project_dir / "AGENTS.md")
