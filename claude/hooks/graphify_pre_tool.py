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

    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    t = data.get("tool_input", data)
    decision = "allow"
    context = None
    session = str(data.get("session_id") or "")
    exists = pathlib.Path("graphify-out/graph.json").exists()
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
                low_cmd = cmd.lower()
                if any(w in low_cmd for w in ["error", "debug", "test", "fix", "bug"]):
                    tool_ctx = "debugging"
                elif any(w in low_cmd for w in ["build", "compile", "make", "install"]):
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
        sys.stdout.write(json.dumps(out))


if __name__ == "__main__":
    main()
