#!/usr/bin/env python3
"""Unified Graphify Pre-Tool hook script for Claude and Gemini."""

import argparse
import json
import os
import pathlib
import shlex
import sys
import tempfile

# Constants
B = (
    'ack', 'ag', 'awk', 'bat', 'cat', 'diff', 'fd', 'find', 'grep', 'head', 'hexdump',
    'jq', 'less', 'ls', 'lzcat', 'more', 'nl', 'od', 'paste', 'rg', 'ripgrep', 'sdff', 'sed',
    'sort', 'strings', 'tail', 'tee', 'uniq', 'wc', 'xxd', 'xzcat', 'yq', 'zcat', 'zless', 'zmore'
)
E = ('.c', '.cc', '.cpp', '.cs', '.go', '.h', '.hpp', '.java', '.js', '.json', '.jsx', '.kt', '.lua', '.md', '.mdx', '.php', '.py', '.rb', '.rs', '.rst', '.scala', '.sh', '.swift', '.toml', '.ts', '.tsx', '.txt', '.yaml', '.yml')
I = ('.claude', '.codex', '.gemini', '.git', 'graphify-out', 'node_modules', 'skills')
DOC_CONTEXT_PARTS = {'docs', 'doc', 'documentation'}
DOC_CONTEXT_EXTENSIONS = {'.md', '.mdx', '.rst', '.txt'}
G = '⚠️ GRAPHIFY WORKFLOW RULES:\n- Architecture questions → rtk graphify query "question"\n- Code relationships → rtk graphify path "A" "B"\n- Deep-dive concepts → rtk graphify explain "concept"\n- Impact analysis / reverse dependencies → rtk graphify affected "SymbolName"\n- Direct reads are ONLY for editing specific files.'


def is_inline_python_file_read(command, executables):
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


def get_graphify_count(session):
    if not session:
        return 0
    safe = "".join(ch for ch in session if ch.isalnum() or ch in "-_")[:120]
    state = pathlib.Path(tempfile.gettempdir()) / ("ai-coding-config-graphify-" + safe + ".count")
    if state.exists():
        try:
            with state.open("r") as handle:
                return int(handle.read().strip() or "0")
        except Exception:
            return 0
    return 0


def payload_cwd(data, tool_input):
    return (
        data.get("cwd")
        or data.get("Cwd")
        or tool_input.get("cwd")
        or tool_input.get("Cwd")
        or os.getcwd()
    )


def is_graph_json_path(raw_path):
    normalized = str(raw_path or "").lower().replace("\\", "/")
    return normalized.endswith("graphify-out/graph.json") or "/graphify-out/graph.json" in normalized


def graph_json_denial():
    return (
        "❌ BLOCKED: `graphify-out/graph.json` is an internal Graphify artifact and must not be read manually.\n"
        "💡 TIP: Use the graphify CLI instead: `rtk graphify query`, `rtk graphify path`, "
        "`rtk graphify explain`, or `rtk graphify affected`. Existence probes like "
        "`test -f graphify-out/graph.json` are allowed."
    )


def is_doc_context_file(raw_path):
    normalized = str(raw_path or "").lower().replace("\\", "/")
    path = pathlib.Path(normalized)
    return path.suffix in DOC_CONTEXT_EXTENSIONS and bool(set(path.parts) & DOC_CONTEXT_PARTS)



def main():
    parser = argparse.ArgumentParser(description="Graphify Hook Classifier")
    parser.add_argument("--tool", required=True, help="Tool name being evaluated (e.g. Bash, Read, Grep)")
    parser.add_argument("--client", required=True, choices=["claude", "gemini"], help="Client type (claude or gemini)")
    args = parser.parse_args()

    TOOL = args.tool
    CLAUDE = (args.client == "claude")

    def find_graph(d, inp):
        def has_g(p):
            try:
                return p.joinpath("graphify-out", "graph.json").exists()
            except Exception:
                return False
        # 1. CWD
        cwd = pathlib.Path().resolve()
        if has_g(cwd):
            return True
        # 2. Walk up parent process chain (Linux)
        try:
            pid = os.getpid()
            while pid > 1:
                try:
                    proc_cwd = pathlib.Path(os.readlink(f"/proc/{pid}/cwd"))
                    if has_g(proc_cwd):
                        return True
                except Exception:
                    pass
                try:
                    with open(f"/proc/{pid}/stat") as fh:
                        pid = int(fh.read().split()[3])
                except Exception:
                    break
        except Exception:
            pass
        # 3. workspacePaths
        wps = list(d.get("workspacePaths", []))
        for key in ("cwd", "Cwd"):
            if key in d:
                wps.append(d[key])
            if key in inp:
                wps.append(inp[key])
        for wp in wps:
            if wp:
                wp_path = pathlib.Path(wp)
                if has_g(wp_path):
                    return True
                try:
                    for sub in wp_path.iterdir():
                        if sub.is_dir() and has_g(sub):
                            return True
                except Exception:
                    pass
        # 4. Path fields
        path_fields = [
            inp.get("file_path"), inp.get("path"), inp.get("pattern"),
            inp.get("AbsolutePath"), inp.get("DirectoryPath"), inp.get("SearchPath"),
        ]
        for val in path_fields:
            if not val:
                continue
            try:
                val_path = pathlib.Path(val).resolve()
                for parent in [val_path, *val_path.parents]:
                    if has_g(parent):
                        return True
                    try:
                        for sub in parent.iterdir():
                            if sub.is_dir() and has_g(sub):
                                return True
                    except Exception:
                        pass
            except Exception:
                pass
        return False

    try:
        raw_stdin = sys.stdin.read()
        data = json.loads(raw_stdin)
    except Exception as exc:
        data = {}

    t = data.get("tool_input", {})
    if not t and "toolCall" in data:
        t = data["toolCall"].get("args", {})
    if not t:
        t = data
    exists = find_graph(data, t)

    try:
        _debug_path = pathlib.Path(__file__).resolve().parent.parent.parent / "hook-debug-claude.json"
        with open(_debug_path, "w") as f:
            f.write(json.dumps({
                "raw_stdin": data,
                "getcwd": os.getcwd(),
                "exists": exists
            }, indent=2))
    except Exception:
        pass

    decision = "allow"
    context = None
    session = str(data.get("session_id") or data.get("conversationId") or "")

    # Compaction suggestion tracking
    if session:
        safe_session = "".join(ch for ch in session if ch.isalnum() or ch in "-_")[:120]
        tool_state_file = pathlib.Path(tempfile.gettempdir()) / f"ai-coding-config-tools-{safe_session}.count"
        
        # Read and increment count
        tool_count = 0
        if tool_state_file.exists():
            try:
                with tool_state_file.open("r") as handle:
                    tool_count = int(handle.read().strip() or "0")
            except Exception:
                pass
        tool_count += 1
        
        try:
            with tool_state_file.open("w") as handle:
                handle.write(str(tool_count))
        except Exception:
            pass
            
        # Suggest compaction at threshold (50) and periodically (every 25 calls after)
        threshold = 50
        if tool_count >= threshold and (tool_count - threshold) % 25 == 0:
            sys.stderr.write(
                f"\n\033[1;33m⚠️ [COMPACTION SUGGESTION] Active session has reached {tool_count} tool calls.\033[0m\n"
                f"\033[1;36m💡 Run `/compact` to save your session progress, then restart your CLI to clear token history.\033[0m\n\n"
            )
    debug = os.environ.get("GRAPHIFY_DEBUG", "0") == "1"
    bypass = os.environ.get("GRAPHIFY_BYPASS", "0") == "1"

    def log(m):
        if debug:
            sys.stderr.write("[GRAPHIFY_HOOK_DEBUG] " + m + "\n")

    if bypass:
        log("Bypass enabled")
        sys.exit(0)

    # Path leak check (independent of Graphify)
    leak_detected = False
    home_dir = str(pathlib.Path.home().as_posix())
    content_fields = {"content", "code_content", "CodeContent", "replacement_content", "ReplacementContent"}

    def contains_leak(val):
        if not isinstance(val, str):
            return False
        return home_dir in val

    def scan_input(obj):
        nonlocal leak_detected
        if leak_detected:
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in content_fields and contains_leak(v):
                    leak_detected = True
                    return
                elif k == "ReplacementChunks" and isinstance(v, list):
                    for chunk in v:
                        if isinstance(chunk, dict) and contains_leak(chunk.get("ReplacementContent")):
                            leak_detected = True
                            return
                scan_input(v)
        elif isinstance(obj, list):
            for item in obj:
                scan_input(item)

    scan_input(t)
    if leak_detected:
        decision = "deny"
        context = f"❌ BLOCKED: Absolute home directory path detected in edit content!\n💡 TIP: Please use relative paths (e.g. `./` or `../`) instead of absolute paths (e.g. `{home_dir}/...`) to prevent leaking your environment."

    if not leak_detected and exists:
        def sq(s):
            s = s.strip()
            while len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
                s = s[1:-1].strip()
            return s

        tool_ctx = "exploration"
        if TOOL == "Edit":
            tool_ctx = "editing"
        else:
            fp = str(t.get("file_path") or t.get("AbsolutePath") or t.get("path") or "")
            if fp and any(m in fp for m in ["IMPROVEMENT", "PLAN", "TODO", "CHANGELOG"]):
                tool_ctx = "planning"
            cmd = sq(str(t.get("command") or t.get("CommandLine") or ""))
            if cmd:
                import re
                low_cmd = cmd.lower()
                words = set(re.findall(r'[a-z]+', low_cmd))
                try:
                    lx = shlex.shlex(cmd, posix=True, punctuation_chars="|&;()")
                    lx.whitespace_split = True
                    tokens = list(lx)
                except ValueError:
                    tokens = []
                ex_names = []
                expect = True
                for token in tokens:
                    if token in {"|", "||", "&&", ";", "(", ")", "&"}:
                        expect = True
                        continue
                    if not expect or ("=" in token and not token.startswith(("/", "./"))):
                        continue
                    word = pathlib.Path(token).name
                    if word in {"rtk", "proxy", "sudo", "command", "builtin", "env", "nohup"}:
                        continue
                    ex_names.append(word)
                    expect = False

                if any(w in words for w in ["error", "debug", "test", "pytest", "vitest", "jest", "unittest", "fix", "bug"]):
                    tool_ctx = "debugging"
                elif any(w in words for w in ["build", "compile", "make", "install"]):
                    if not any(w in B for w in ex_names):
                        tool_ctx = "building"

        log("Context: " + tool_ctx)

        if TOOL == "Grep":
            decision = "deny"
            context = "❌ BLOCKED: Direct search/read tools are not available for exploration.\n💡 CRITICAL: Answer from your existing Graphify context. Do NOT retry this call or attempt alternative read methods — they will also be blocked."
        elif TOOL == "Bash":
            raw = sq(str(t.get("command") or t.get("CommandLine") or ""))
            low = raw.lower().replace(chr(92), "/")
            try:
                lx = shlex.shlex(raw, posix=True, punctuation_chars="|&;()")
                lx.whitespace_split = True
                tokens = list(lx)
            except ValueError:
                tokens = []
            ex = []
            expect = True
            for token in tokens:
                if token in {"|", "||", "&&", ";", "(", ")", "&"}:
                    expect = True
                    continue
                if not expect or ("=" in token and not token.startswith(("/", "./"))):
                    continue
                word = pathlib.Path(token).name
                if word in {"rtk", "proxy", "sudo", "command", "builtin", "env", "nohup"}:
                    continue
                ex.append(word)
                expect = False
            words = [pathlib.Path(token).name.lower() for token in tokens]
            probe = ("graphify-out/graph.json" in low and any(word in {"test", "[", "ls", "stat"} for word in words))
            graph_call = "graphify" in ex and any(("graphify " + sub) in low for sub in ("query", "path", "explain", "affected"))
            over_quota = False
            if graph_call and session:
                safe = "".join(ch for ch in session if ch.isalnum() or ch in "-_")[:120]
                state = pathlib.Path(tempfile.gettempdir()) / ("ai-coding-config-graphify-" + safe + ".count")
                with state.open("a+") as handle:
                    try:
                        import fcntl
                        fcntl.flock(handle, fcntl.LOCK_EX)
                    except (ImportError, AttributeError, PermissionError, OSError):
                        try:
                            import msvcrt
                            msvcrt.locking(handle.fileno(), 1, 1)
                        except (ImportError, PermissionError, OSError):
                            pass
                    handle.seek(0)
                    try:
                        count = int(handle.read().strip() or "0")
                    except ValueError:
                        count = 0
                    over_quota = count >= 20
                    if not over_quota:
                        handle.seek(0)
                        handle.truncate()
                        handle.write(str(count + 1))
                        handle.flush()
                    try:
                        import fcntl
                        fcntl.flock(handle, fcntl.LOCK_UN)
                    except (ImportError, AttributeError, PermissionError, OSError):
                        try:
                            import msvcrt
                            msvcrt.locking(handle.fileno(), 0, 1)
                        except (ImportError, PermissionError, OSError):
                            pass
            if over_quota:
                decision = "deny"
                context = "❌ BLOCKED: Maximum 20 Graphify discovery calls reached for this session.\n💡 TIP: Synthesize the answer from available context. Do not attempt direct reads; they are strictly prohibited and will remain blocked."
            elif "graphify-out/graph.json" in low and not probe:
                decision = "deny"
                context = graph_json_denial()
            elif probe:
                log("Probe allowed")
            elif is_inline_python_file_read(raw, ex):
                decision = "deny"
                context = "❌ BLOCKED: Inline script execution for exploration is blocked.\n💡 CRITICAL: Answer from your existing Graphify context. Do NOT retry this call or attempt alternative read methods — they will also be blocked."
            elif any(word in B for word in ex):
                B_search = {'ack', 'ag', 'fd', 'find', 'grep', 'ls', 'rg', 'ripgrep'}
                g_count = get_graphify_count(session)
                is_allowed_post_graphify = (g_count >= 1 and not any(word in B_search for word in ex))
                if tool_ctx not in {"debugging", "building"} and not is_allowed_post_graphify:
                    decision = "deny"
                    context = "❌ BLOCKED: Direct search/read tools are not available for exploration.\n💡 CRITICAL: Answer from your existing Graphify context. Do NOT retry this call or attempt alternative read methods — they will also be blocked."
        elif TOOL in {"Read", "Glob"}:
            fp = str(
                t.get("file_path")
                or t.get("AbsolutePath")
                or t.get("DirectoryPath")
                or t.get("SearchPath")
                or t.get("path")
                or ""
            )
            if fp:
                p = fp.lower().replace(chr(92), "/")
                parts = set(pathlib.Path(p).parts)
                if is_graph_json_path(p):
                    decision = "deny"
                    context = graph_json_denial()
                elif not parts.intersection(I):
                    suffix = pathlib.Path(p).suffix
                    looks_like_directory = not suffix
                    is_source_or_doc = suffix in E or looks_like_directory
                    g_count = get_graphify_count(session)
                    if (
                        is_source_or_doc
                        and g_count == 0
                        and tool_ctx not in {"editing", "planning", "debugging"}
                        and not is_doc_context_file(p)
                    ):
                        decision = "deny"
                        context = "❌ BLOCKED: Direct search/read tools are not available for exploration.\n💡 CRITICAL: Answer from your existing Graphify context. Do NOT retry this call or attempt alternative read methods — they will also be blocked."

    if CLAUDE:
        out = {}
        if context:
            out = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": context,
                    "permissionDecision": decision
                }
            }
            if decision == "deny":
                out["hookSpecificOutput"].update({"permissionDecisionReason": context})
        sys.stdout.write(json.dumps(out) if out else "")
    else:
        out = {"decision": decision}
        if context:
            out["reason"] = context
        sys.stdout.write(json.dumps(out))


if __name__ == "__main__":
    main()
