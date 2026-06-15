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
B = ('ack', 'ag', 'bat', 'cat', 'fd', 'find', 'grep', 'head', 'less', 'more', 'rg', 'ripgrep', 'tail', 'wc')
E = ('.c', '.cc', '.cpp', '.cs', '.go', '.h', '.hpp', '.java', '.js', '.json', '.jsx', '.kt', '.lua', '.md', '.mdx', '.php', '.py', '.rb', '.rs', '.rst', '.scala', '.sh', '.swift', '.toml', '.ts', '.tsx', '.txt', '.yaml', '.yml')
I = ('.claude', '.codex', '.gemini', '.git', 'graphify-out', 'node_modules', 'skills')
G = '⚠️ GRAPHIFY WORKFLOW RULES:\n- Architecture questions → rtk graphify query "question"\n- Code relationships → rtk graphify path "A" "B"\n- Deep-dive concepts → rtk graphify explain "concept"\n- Impact analysis / reverse dependencies → rtk graphify affected "SymbolName"\n- Direct reads are ONLY for editing specific files.'


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
        if "cwd" in d:
            wps.append(d["cwd"])
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
    session = str(data.get("session_id") or "")
    debug = os.environ.get("GRAPHIFY_DEBUG", "0") == "1"
    bypass = os.environ.get("GRAPHIFY_BYPASS", "0") == "1"

    def log(m):
        if debug:
            sys.stderr.write("[GRAPHIFY_HOOK_DEBUG] " + m + "\n")

    if bypass:
        log("Bypass enabled")
        sys.exit(0)

    if exists:
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
                    if word in {"rtk", "sudo", "command", "builtin", "env", "nohup"}:
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
            context = "❌ BLOCKED: Grep is blocked for codebase exploration\n💡 TIP: Use `graphify query \"your question\"` for codebase exploration"
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
                if word in {"rtk", "sudo", "command", "builtin", "env", "nohup"}:
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
                    over_quota = count >= 3
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
                context = "❌ BLOCKED: Maximum 3 Graphify discovery calls reached for this session.\n💡 TIP: Synthesize the answer from available context."
            elif probe:
                log("Probe allowed")
            elif any(word in B for word in ex):
                if tool_ctx not in {"debugging", "building"}:
                    decision = "deny"
                    context = "❌ BLOCKED: Search tools are blocked for codebase exploration\n💡 TIP: Use `graphify query \"your question\"` for codebase exploration"
        elif TOOL in {"Read", "Glob"}:
            fp = str(t.get("file_path") or t.get("AbsolutePath") or t.get("path") or "")
            if fp:
                p = fp.lower().replace(chr(92), "/")
                parts = set(pathlib.Path(p).parts)
                if not parts.intersection(I) and pathlib.Path(p).suffix in E:
                    if tool_ctx not in {"editing", "planning"}:
                        decision = "deny"
                        context = "❌ BLOCKED: Reading source files for exploration is blocked\n💡 TIP: Use `graphify query \"what you want to know\"` instead of reading " + pathlib.Path(fp).name

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
            out["additionalContext"] = context
            out["reason"] = context
        sys.stdout.write(json.dumps(out))


if __name__ == "__main__":
    main()
