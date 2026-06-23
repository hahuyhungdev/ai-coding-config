"""Graphify hook policy and project-level config merging."""

import json
import os
import shlex
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from installer.constants import CLAUDE_DIR, GEMINI_DIR, GEMINI_CLI_DIR, REPO_DIR, REAL_HOME


MANAGED_GRAPHIFY_MARKER = "ai-coding-config:graphify-managed"
BROAD_DISCOVERY_COMMANDS = {
    "ack", "ag", "awk", "bat", "cat", "diff", "fd", "find", "grep", "head", "hexdump",
    "jq", "less", "ls", "lzcat", "more", "nl", "od", "paste", "rg", "ripgrep", "sdff", "sed",
    "sort", "strings", "tail", "tee", "uniq", "wc", "xxd", "xzcat", "yq", "zcat", "zless", "zmore"
}
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
- For codebase exploration, use **Graphify-only**. Do NOT use view_file, list_dir, cat, grep, sed, awk, or inline scripts to explore.
- Use at most **20 Graphify calls** total per question. After 20 calls, hard stop and synthesize from available context.
- **Focus queries on specific symbols** — prefer `graphify query "what does X do"` over `graphify query "explain the codebase"`.
- **Synthesize from Graphify context only.** Answer based on what Graphify returns. Do not supplement with direct file reads for exploration.
- **If a tool call is blocked, do not retry.** Proceed and answer using the available context.
- Dirty `graphify-out/` files are expected after hooks or incremental updates and are not a reason to skip Graphify.
- Do not manually read or parse graphify-out/graph.json; it is an internal artifact. Use the graphify CLI (`rtk graphify query/path/explain/affected`) instead. Existence probes such as `test -f graphify-out/graph.json` are acceptable.
- If `graphify-out/wiki/index.md` exists, use it for broad navigation instead of raw source browsing.
- Read `graphify-out/GRAPH_REPORT.md` only when scoped queries are insufficient or the user requests a broad report.

Post-Discovery Reads (exceptions):
- After Graphify discovery, targeted raw reads ARE allowed for: **editing**, **debugging**, and **config review** of specific files already identified by Graphify.
- You MUST have run at least one Graphify query before reading source files directly.
- When reading after discovery, state your justification (e.g., "Reading for editing" or "Verifying config structure").
- After modifying code, run `graphify update .`.

Blocked Tool Recovery:
- If a hook blocks a direct read/search or inline script, do not retry the same blocked call or attempt an equivalent bypass.
- Do not spawn subagents or fresh sessions to bypass blocked tools, Graphify quota, or current session scope restrictions.
- Do not create one-off scratch scripts to inspect facts that a project diagnostic already covers.
- For conversation log debugging in this repo, use `rtk python3 scripts/inspect_conversation.py <conversation_id> --step-index <n> --keyword "<text>"`; add `--compare-logs` when comparing compact vs full transcripts.
- When debugging truncation, measure full content length and keyword presence; do not use substring-only previews as evidence.
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


def is_inline_python_file_read(command: str, executables: list[str]) -> bool:
    import shlex
    import re
    lowered = command.lower()
    try:
        lx = shlex.shlex(command, posix=True, punctuation_chars="|&;()")
        lx.whitespace_split = True
        tokens = list(lx)
    except ValueError:
        tokens = []

    has_inline_flag = False
    for t in tokens:
        if t == "--eval":
            has_inline_flag = True
            break
        if t.startswith("-") and not t.startswith("--"):
            flag_chars = t[1:]
            if any(c in flag_chars for c in ("c", "e", "r", "p", "n", "E")):
                has_inline_flag = True
                break
    if not has_inline_flag:
        if any(marker in lowered for marker in ("<<", "<<<")):
            has_inline_flag = True

    if not has_inline_flag:
        return False

    has_read_keyword = any(kw in lowered for kw in ("open", "read", "load", "file", "listdir", "scandir", "walk", "glob"))
    if not has_read_keyword:
        return False

    interpreters = {"python", "node", "perl", "ruby", "php", "deno", "bun"}
    for ex in executables:
        name = ex.lower()
        name_base = name.split(".")[0]
        name_clean = re.sub(r'\d+$', '', name_base)
        if name_clean in interpreters:
            return True

    return False


def _command_words(command: str) -> list[str]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars="|&;()")
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return []

    executables = []
    expect_command = True
    wrappers = {"rtk", "proxy", "sudo", "command", "builtin", "env", "nohup"}
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


def is_graph_json_path(raw_path: object) -> bool:
    normalized = str(raw_path or "").lower().replace("\\", "/")
    return normalized.endswith("graphify-out/graph.json") or "/graphify-out/graph.json" in normalized


def graph_json_denial_context() -> str:
    return (
        "❌ BLOCKED: `graphify-out/graph.json` is an internal Graphify artifact and must not be read manually.\n"
        "💡 TIP: Use the graphify CLI instead: `rtk graphify query`, `rtk graphify path`, "
        "`rtk graphify explain`, or `rtk graphify affected`. Existence probes like "
        "`test -f graphify-out/graph.json` are allowed."
    )


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
            "additionalContext": "❌ BLOCKED: Direct search/read tools are not available for exploration.\n💡 CRITICAL: Answer from your existing Graphify context. Do NOT retry this call or attempt alternative read methods — they will also be blocked.",
        }
    if tool_name.lower() == "bash":
        command = str(tool_input.get("command") or tool_input.get("CommandLine") or "")
        if is_graphify_probe_command(command):
            return {"decision": "allow"}
        if is_graph_json_path(command):
            return {
                "decision": "deny",
                "additionalContext": graph_json_denial_context(),
            }
        executables = _command_words(command)
        if is_inline_python_file_read(command, executables):
            return {
                "decision": "deny",
                "additionalContext": "❌ BLOCKED: Inline script execution for exploration is blocked.\n💡 CRITICAL: Answer from your existing Graphify context. Do NOT retry this call or attempt alternative read methods — they will also be blocked.",
            }
        if is_broad_discovery_command(command):
            return {
                "decision": "deny",
                "additionalContext": "❌ BLOCKED: Direct search/read tools are not available for exploration.\n💡 CRITICAL: Answer from your existing Graphify context. Do NOT retry this call or attempt alternative read methods — they will also be blocked.",
            }
    if tool_name.lower() in {"read", "glob", "read_file", "list_directory"}:
        if any(is_graph_json_path(value) for value in tool_input.values()):
            return {
                "decision": "deny",
                "additionalContext": graph_json_denial_context(),
            }
    if tool_name.lower() in {"read", "glob", "read_file", "list_directory"} and is_source_tool_input(tool_input):
        return {
            "decision": "deny",
            "additionalContext": "❌ BLOCKED: Direct search/read tools are not available for exploration.\n💡 CRITICAL: Answer from your existing Graphify context. Do NOT retry this call or attempt alternative read methods — they will also be blocked.",
        }
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
        home_str = str(REAL_HOME.as_posix())
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
        {"matcher": "Write", "hooks": [{"type": "command", "command": _python_hook_command("Write", True, project_level)}]},
        {"matcher": "Edit", "hooks": [{"type": "command", "command": _python_hook_command("Edit", True, project_level)}]},
    ]


def managed_gemini_hooks(project_level: bool = False) -> list[dict]:
    return [
        {"matcher": "run_command|run_shell_command", "hooks": [{"type": "command", "command": _python_hook_command("Bash", False, project_level)}]},
        {"matcher": "view_file|list_dir|read_file|list_directory", "hooks": [{"type": "command", "command": _python_hook_command("Read", False, project_level)}]},
        {"matcher": "grep_search", "hooks": [{"type": "command", "command": _python_hook_command("Grep", False, project_level)}]},
        {"matcher": "write_to_file|replace_file_content|multi_replace_file_content", "hooks": [{"type": "command", "command": _python_hook_command("Write", False, project_level)}]},
    ]


def managed_codex_hooks(project_level: bool = False) -> list[dict]:
    return [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": _python_hook_command("Bash", True, project_level, client="codex")}]},
        {"matcher": "Grep", "hooks": [{"type": "command", "command": _python_hook_command("Grep", True, project_level, client="codex")}]},
        {"matcher": "Read|Glob", "hooks": [{"type": "command", "command": _python_hook_command("Read", True, project_level, client="codex")}]},
        {"matcher": "Write", "hooks": [{"type": "command", "command": _python_hook_command("Write", True, project_level, client="codex")}]},
        {"matcher": "Edit", "hooks": [{"type": "command", "command": _python_hook_command("Edit", True, project_level, client="codex")}]},
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
        merged = before.rstrip() + ("\n\n" if before.strip() else "") + PROJECT_GRAPHIFY_BLOCK + after
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
    global_dir = CLAUDE_DIR
    global_hooks_dir = global_dir / "hooks"
    global_hooks_dir.mkdir(parents=True, exist_ok=True)

    # Ensure global script exists
    repo_dir = REPO_DIR
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
    global_dir = GEMINI_CLI_DIR
    global_hooks_dir = global_dir / "hooks"
    global_hooks_dir.mkdir(parents=True, exist_ok=True)

    # Ensure global script exists
    repo_dir = REPO_DIR
    repo_hook = repo_dir / "claude" / "hooks" / "graphify_pre_tool.py"
    _safe_copy(repo_hook, global_hooks_dir / "graphify_pre_tool.py")

    # Ensure project-level script exists
    local_hook_dir = project_dir / ".gemini" / "hooks"
    _safe_copy(repo_hook, local_hook_dir / "graphify_pre_tool.py")

    global_settings = global_dir / "settings.json"
    _merge_managed_hooks(global_settings, "PreToolUse", managed_gemini_hooks(project_level=False))
    _merge_managed_hooks(project_dir / ".gemini" / "settings.json", "PreToolUse", managed_gemini_hooks(project_level=True))

    # Configure global plugin hooks directly referencing the unified pre-tool script
    plugin_hooks = GEMINI_DIR / "plugins" / "graphify" / "hooks.json"
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
