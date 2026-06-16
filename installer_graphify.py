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
BROAD_DISCOVERY_COMMANDS = {"grep", "rg", "ripgrep", "find", "fd", "ack", "ag", "head", "cat", "tail", "less", "more", "bat", "wc"}
SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb",
    ".c", ".h", ".cpp", ".hpp", ".cc", ".cs", ".kt", ".swift", ".php",
    ".scala", ".lua", ".sh", ".md", ".rst", ".txt", ".mdx",
    ".json", ".yaml", ".yml", ".toml",
}
IGNORED_SOURCE_PARTS = {
    "graphify-out", "skills", ".claude", ".gemini", ".codex", ".git", "node_modules",
}
GRAPHIFY_GUIDANCE = (
    "⚠️ GRAPHIFY WORKFLOW RULES (MANDATORY — READ BEFORE ANY CODEBASE EXPLORATION):\n\n"
    "**CRITICAL: For ANY question about codebase structure, architecture, or file relationships, your VERY FIRST tool call MUST be `rtk graphify query \"<question>\"`. Do NOT use `list_dir`, `grep_search`, `find`, `cat`, or `view_file` as your first exploration step. Graphify-first is non-negotiable.**\n\n"
    "Commands:\n"
    "- Architecture questions → `rtk graphify query \"question\"`\n"
    "- Code relationships → `rtk graphify path \"A\" \"B\"`\n"
    "- Deep-dive concepts → `rtk graphify explain \"concept\"`\n"
    "- Impact analysis / reverse dependencies → `rtk graphify affected \"SymbolName\"`"
)
GRAPHIFY_INSTRUCTIONS = f"""## graphify

{GRAPHIFY_GUIDANCE}

Rules:
- For an architecture question, the FIRST tool call must be one broad `rtk graphify query "<question>"`. Do not check Graphify with `ls`, `which`, or `test` first.
- Do NOT use `list_dir` → `grep_search` as a discovery pattern. This is explicitly prohibited. Use Graphify instead.
- Use at most 3 Graphify calls total: the initial query plus at most 2 follow-up `query`, `path`, `explain` or `affected` calls. After the third call, hard stop all Graphify calls and synthesize the answer from available context.
- Dirty `graphify-out/` files are expected after hooks or incremental updates and are not a reason to skip Graphify.
- If `graphify-out/wiki/index.md` exists, use it for broad navigation instead of raw source browsing.
- Read `graphify-out/GRAPH_REPORT.md` only when scoped queries are insufficient or the user requests a broad report.

Post-Discovery Reads:
- After Graphify discovery, targeted raw reads ARE allowed for: **editing**, **debugging**, **config review**, and **precise verification** of specific files identified by Graphify.
- You MUST have run at least one Graphify query before reading source files directly.
- When reading after discovery, state your justification (e.g., "Reading for editing" or "Verifying config structure").
- After modifying code, run `graphify update .`.
"""
INSTRUCTION_START = "<!-- ai-coding-config:graphify-start -->"
INSTRUCTION_END = "<!-- ai-coding-config:graphify-end -->"
PROJECT_GRAPHIFY_BLOCK = f"{INSTRUCTION_START}\n{GRAPHIFY_INSTRUCTIONS.rstrip()}\n{INSTRUCTION_END}"
ANTIGRAVITY_RTK_RULE = """# RTK - Rust Token Killer (Google Antigravity)

**Usage**: Token-optimized CLI proxy for shell commands.

## Rule

Always prefix shell commands with `rtk` to minimize token consumption.

Examples:

```bash
rtk git status
rtk cargo test
rtk ls src/
rtk grep "pattern" src/
rtk find "*.rs" .
rtk docker ps
rtk gh pr list
```

> ⚠️ **Note**: While `rtk grep` and `rtk find` are supported for targeted lookup, codebase and architecture exploration should always use Graphify first (`rtk graphify query`, etc.) to preserve context and save tokens.

## Meta Commands

```bash
rtk gain              # Show token savings
rtk gain --history    # Command history with savings
rtk discover          # Find missed RTK opportunities
rtk proxy <cmd>       # Run raw (no filtering, for debugging)
```

## Why

RTK filters and compresses command output before it reaches the LLM context, saving 60-90% tokens on common operations. Always use `rtk <cmd>` instead of raw commands.
"""


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
    repo_dir = Path(__file__).resolve().parent
    hook_file = repo_dir / "claude" / "hooks" / "graphify_pre_tool.py"
    if hook_file.exists():
        content = hook_file.read_text(encoding="utf-8")
    else:
        raise FileNotFoundError(f"graphify_pre_tool.py not found at {hook_file}")
    client = "claude" if claude else "gemini"
    header = f"import sys\nsys.argv = [sys.executable, '--tool', {tool_name!r}, '--client', {client!r}]\n"
    return header + content


def _python_hook_command(tool_name: str, claude: bool, project_level: bool = False, client: str = None) -> str:
    py = "python3" if sys.platform != "win32" else "python"
    actual_client = client if client else ("claude" if claude else "gemini")
    if project_level:
        hook_path = f".{actual_client}/hooks/graphify_pre_tool.py"
    else:
        # Global path
        home_str = str(Path.home().as_posix())
        if actual_client == "claude":
            hook_path = f"{home_str}/.claude/hooks/graphify_pre_tool.py"
        elif actual_client == "gemini":
            hook_path = f"{home_str}/.gemini/antigravity-cli/hooks/graphify_pre_tool.py"
        else:
            hook_path = f"{home_str}/.{actual_client}/hooks/graphify_pre_tool.py"
    hook_client = "claude" if actual_client in ("claude", "codex") else "gemini"
    return f"# {MANAGED_GRAPHIFY_MARKER}\n{py} \"{hook_path}\" --tool {tool_name} --client {hook_client}"


def managed_claude_hooks(project_level: bool = False) -> list[dict]:
    return [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": _python_hook_command("Bash", True, project_level)}]},
        {"matcher": "Grep", "hooks": [{"type": "command", "command": _python_hook_command("Grep", True, project_level)}]},
        {"matcher": "Read|Glob", "hooks": [{"type": "command", "command": _python_hook_command("Read", True, project_level)}]},
    ]


def managed_gemini_hooks(project_level: bool = False) -> list[dict]:
    return [
        {"matcher": "run_command|run_shell_command", "hooks": [{"type": "command", "command": _python_hook_command("Bash", False, project_level)}]},
        {"matcher": "view_file|list_dir|read_file|list_directory", "hooks": [{"type": "command", "command": _python_hook_command("Read", False, project_level)}]},
        {"matcher": "grep_search", "hooks": [{"type": "command", "command": _python_hook_command("Grep", False, project_level)}]},
    ]


def managed_codex_hooks(project_level: bool = False) -> list[dict]:
    return [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": _python_hook_command("Bash", True, project_level, client="codex")}]},
        {"matcher": "Grep", "hooks": [{"type": "command", "command": _python_hook_command("Grep", True, project_level, client="codex")}]},
        {"matcher": "Read|Glob", "hooks": [{"type": "command", "command": _python_hook_command("Read", True, project_level, client="codex")}]},
    ]


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
    if "settings.json" in path.name.lower():
        settings["enableJsonHooks"] = True
        settings["enable_json_hooks"] = True
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


def _ensure_antigravity_rtk_rule(project_dir: Path) -> None:
    rules_path = project_dir / ".agents" / "rules" / "antigravity-rtk-rules.md"
    if rules_path.exists():
        return
    rules_path.parent.mkdir(parents=True, exist_ok=True)
    rules_path.write_text(ANTIGRAVITY_RTK_RULE, encoding="utf-8")


def _safe_copy(src: Path, dst: Path) -> None:
    if src.exists() and src.resolve() != dst.resolve():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def configure_claude_project(project_dir: Path) -> None:
    global_dir = Path.home() / ".claude"
    global_hooks_dir = global_dir / "hooks"
    global_hooks_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure global script exists
    repo_dir = Path(__file__).resolve().parent
    repo_hook = repo_dir / "claude" / "hooks" / "graphify_pre_tool.py"
    _safe_copy(repo_hook, global_hooks_dir / "graphify_pre_tool.py")

    # Ensure project-level hooks directory exists and copy the script
    local_hook_dir = project_dir / ".claude" / "hooks"
    local_hook_dir.mkdir(parents=True, exist_ok=True)
    _safe_copy(repo_hook, local_hook_dir / "graphify_pre_tool.py")

    global_settings = global_dir / "settings.json"
    _merge_managed_hooks(global_settings, "PreToolUse", managed_claude_hooks(project_level=False))
    _merge_managed_hooks(project_dir / ".claude" / "settings.json", "PreToolUse", managed_claude_hooks(project_level=True))
    if (project_dir / "graphify-out" / "graph.json").exists():
        _merge_project_instructions(project_dir / "CLAUDE.md")


def configure_gemini_project(project_dir: Path) -> None:
    global_dir = Path.home() / ".gemini" / "antigravity-cli"
    global_hooks_dir = global_dir / "hooks"
    global_hooks_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure global script exists
    repo_dir = Path(__file__).resolve().parent
    repo_hook = repo_dir / "claude" / "hooks" / "graphify_pre_tool.py"
    _safe_copy(repo_hook, global_hooks_dir / "graphify_pre_tool.py")
    
    # Ensure project-level script exists
    local_hook_dir = project_dir / ".gemini" / "hooks"
    _safe_copy(repo_hook, local_hook_dir / "graphify_pre_tool.py")

    global_settings = global_dir / "settings.json"
    _merge_managed_hooks(global_settings, "PreToolUse", managed_gemini_hooks(project_level=False))
    _merge_managed_hooks(project_dir / ".gemini" / "settings.json", "PreToolUse", managed_gemini_hooks(project_level=True))
    
    # Configure global plugin hooks directly referencing the unified pre-tool script
    plugin_hooks = Path.home() / ".gemini" / "config" / "plugins" / "graphify" / "hooks.json"
    _merge_managed_hooks(plugin_hooks, "PreToolUse", managed_gemini_hooks(project_level=False))

    # Clean up legacy BeforeTool hooks if they exist in settings or plugin hooks
    for path in [global_settings, project_dir / ".gemini" / "settings.json", plugin_hooks]:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if "hooks" in data and "BeforeTool" in data["hooks"]:
                    data["hooks"]["BeforeTool"] = [
                        h for h in data["hooks"]["BeforeTool"]
                        if not is_managed_graphify_hook(h)
                    ]
                    if not data["hooks"]["BeforeTool"]:
                        del data["hooks"]["BeforeTool"]
                    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            except Exception:
                pass

    if (project_dir / "graphify-out" / "graph.json").exists():
        _merge_project_instructions(project_dir / "ANTIGRAVITY.md")
    _ensure_antigravity_rtk_rule(project_dir)


def configure_codex_project(project_dir: Path) -> None:
    codex_dir = project_dir / ".codex"
    if codex_dir.exists() and not codex_dir.is_dir():
        _backup_path(codex_dir)
    codex_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure project-level hooks directory exists and copy the script
    repo_dir = Path(__file__).resolve().parent
    repo_hook = repo_dir / "claude" / "hooks" / "graphify_pre_tool.py"
    local_hook_dir = codex_dir / "hooks"
    local_hook_dir.mkdir(parents=True, exist_ok=True)
    _safe_copy(repo_hook, local_hook_dir / "graphify_pre_tool.py")

    _merge_managed_hooks(codex_dir / "hooks.json", "PreToolUse", managed_codex_hooks(project_level=True))
    if (project_dir / "graphify-out" / "graph.json").exists():
        _merge_project_instructions(project_dir / "AGENTS.md")


def configure_copilot_project(project_dir: Path) -> None:
    # 1. VS Code settings
    vscode_dir = project_dir / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    settings_path = vscode_dir / "settings.json"
    
    repo_dir = Path(__file__).resolve().parent
    template_settings_path = repo_dir / "copilot" / "settings.json"
    
    if template_settings_path.exists():
        try:
            with template_settings_path.open("r", encoding="utf-8") as f:
                default_settings = json.load(f)
        except Exception:
            default_settings = {}
    else:
        default_settings = {}
        
    if settings_path.exists():
        try:
            with settings_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}
            
        instructions = data.setdefault("github.copilot.chat.codeGeneration.instructions", [])
        if not isinstance(instructions, list):
            instructions = []
            data["github.copilot.chat.codeGeneration.instructions"] = instructions
            
        file_path_exists = False
        for item in instructions:
            if isinstance(item, dict) and item.get("filePath") == ".github/copilot-instructions.md":
                file_path_exists = True
                break
        if not file_path_exists:
            instructions.append({"filePath": ".github/copilot-instructions.md"})
            
        search_ex = data.setdefault("search.exclude", {})
        if not isinstance(search_ex, dict):
            search_ex = {}
            data["search.exclude"] = search_ex
        if "search.exclude" in default_settings:
            for k, v in default_settings["search.exclude"].items():
                search_ex[k] = v
                
        watcher_ex = data.setdefault("files.watcherExclude", {})
        if not isinstance(watcher_ex, dict):
            watcher_ex = {}
            data["files.watcherExclude"] = watcher_ex
        if "files.watcherExclude" in default_settings:
            for k, v in default_settings["files.watcherExclude"].items():
                watcher_ex[k] = v
                
        try:
            with settings_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
        except Exception as exc:
            sys.stderr.write(f"[WARN] Failed to write to {settings_path}: {exc}\n")
    else:
        if template_settings_path.exists():
            try:
                shutil.copy(str(template_settings_path), str(settings_path))
            except Exception as exc:
                sys.stderr.write(f"[WARN] Failed to copy {template_settings_path} to {settings_path}: {exc}\n")
        else:
            try:
                with settings_path.open("w", encoding="utf-8") as f:
                    json.dump(default_settings, f, indent=2)
                    f.write("\n")
            except Exception as exc:
                sys.stderr.write(f"[WARN] Failed to write {settings_path}: {exc}\n")
                
    # 2. Copilot instructions.md merge
    github_dir = project_dir / ".github"
    github_dir.mkdir(parents=True, exist_ok=True)
    copilot_instructions_path = github_dir / "copilot-instructions.md"
    
    if not copilot_instructions_path.exists():
        template_instructions = repo_dir / "copilot" / "copilot-instructions.md"
        if template_instructions.exists():
            try:
                shutil.copy(str(template_instructions), str(copilot_instructions_path))
            except Exception as exc:
                sys.stderr.write(f"[WARN] Failed to copy {template_instructions} to {copilot_instructions_path}: {exc}\n")
                
    if (project_dir / "graphify-out" / "graph.json").exists():
        _merge_project_instructions(copilot_instructions_path)
