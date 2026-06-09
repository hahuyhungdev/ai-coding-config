#!/usr/bin/env python3
"""
Improved Graphify Hook - Less aggressive, more debuggable, user-friendly

Improvements:
1. Context-aware blocking (editing vs exploration)
2. Actionable error messages with alternatives
3. Verbose logging mode (GRAPHIFY_DEBUG=1)
4. Temporary bypass mechanism (GRAPHIFY_BYPASS=1)
5. Better false positive detection
"""

import json
import os
import pathlib
import shlex
import sys
import tempfile
from typing import Optional, Tuple

# Cross-platform file locking
try:
    import fcntl
    def lock_file(f):
        fcntl.flock(f, fcntl.LOCK_EX)
    def unlock_file(f):
        fcntl.flock(f, fcntl.LOCK_UN)
except ImportError:
    try:
        import msvcrt
        def lock_file(f):
            try:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
            except Exception:
                pass
        def unlock_file(f):
            try:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            except Exception:
                pass
    except ImportError:
        def lock_file(f): pass
        def unlock_file(f): pass

# Configuration
BLOCKED_TOOLS = {'ack', 'ag', 'fd', 'find', 'grep', 'rg', 'ripgrep'}
CODE_EXTENSIONS = {
    '.c', '.cc', '.cpp', '.cs', '.go', '.h', '.hpp', '.java', '.js', '.jsx',
    '.kt', '.lua', '.md', '.mdx', '.php', '.py', '.rb', '.rs', '.rst',
    '.scala', '.sh', '.swift', '.ts', '.tsx', '.txt'
}
IGNORED_DIRS = {'.claude', '.codex', '.gemini', '.git', 'graphify-out', 'node_modules', 'skills'}
QUOTA_LIMIT = 3

# Debug mode
DEBUG = os.environ.get('GRAPHIFY_DEBUG', '0') == '1'
BYPASS = os.environ.get('GRAPHIFY_BYPASS', '0') == '1'

def log_debug(message: str) -> None:
    """Log debug messages if debug mode is enabled."""
    if DEBUG:
        print(f"[GRAPHIFY_HOOK_DEBUG] {message}", file=sys.stderr)

def get_context_from_tool_input(tool_input: dict, tool_name: str) -> str:
    """Detect context from tool input to determine if read is for editing or exploration."""
    # Check if this is an Edit tool call (editing context)
    if tool_name == 'Edit':
        return 'editing'

    # Check if file_path suggests editing (e.g., reading to edit)
    file_path = tool_input.get('file_path', '')
    if file_path:
        # If reading a file that's likely being edited
        if any(marker in file_path for marker in ['IMPROVEMENT', 'PLAN', 'TODO', 'CHANGELOG']):
            return 'planning'

    # Check command context for debugging
    command = tool_input.get('command', '')
    if command:
        low_cmd = command.lower()
        # Debugging context
        if any(word in low_cmd for word in ['error', 'debug', 'test', 'fix', 'bug']):
            return 'debugging'
        # Build/compile context
        if any(word in low_cmd for word in ['build', 'compile', 'make', 'install']):
            return 'building'

    return 'exploration'

def format_error_message(reason: str, context: str, tool_name: str, file_path: str = '') -> str:
    """Format user-friendly error message with actionable guidance."""
    base_msg = f"❌ BLOCKED: {reason}"

    if context == 'editing':
        return f"{base_msg}\n✅ ALTERNATIVE: Use Edit tool directly to modify this file"
    elif context == 'debugging':
        return f"{base_msg}\n✅ ALTERNATIVE: Use `graphify explain \"concept\"` for code understanding"
    elif context == 'building':
        return f"{base_msg}\n✅ ALTERNATIVE: Build commands are allowed - check command syntax"
    elif context == 'planning':
        return f"{base_msg}\n✅ ALTERNATIVE: Use `graphify query \"question\"` for architecture questions"
    else:  # exploration
        if file_path:
            return f"{base_msg}\n💡 TIP: Use `graphify query \"what you want to know\"` instead of reading {pathlib.Path(file_path).name}"
        else:
            return f"{base_msg}\n💡 TIP: Use `graphify query \"your question\"` for codebase exploration"

def check_quota(session: str) -> Tuple[bool, int]:
    """Check if graphify quota is exceeded."""
    if not session:
        return False, 0

    safe = "".join(ch for ch in session if ch.isalnum() or ch in "-_")[:120]
    state_file = pathlib.Path(tempfile.gettempdir()) / f"ai-coding-config-graphify-{safe}.count"

    try:
        with state_file.open("a+") as handle:
            lock_file(handle)
            handle.seek(0)
            try:
                count = int(handle.read().strip() or "0")
            except ValueError:
                count = 0

            over_quota = count >= QUOTA_LIMIT
            if not over_quota:
                handle.seek(0)
                handle.truncate()
                handle.write(str(count + 1))
                handle.flush()

            unlock_file(handle)
            return over_quota, count
    except Exception as e:
        log_debug(f"Quota check error: {e}")
        return False, 0

def is_graphify_call(command: str) -> bool:
    """Check if command is a graphify call."""
    low = command.lower()
    return 'graphify' in low and any(sub in low for sub in ['query', 'path', 'explain'])

def is_probe_command(command: str) -> bool:
    """Check if command is probing graphify installation."""
    low = command.lower()
    words = low.split()
    return (
        ('graphify-out/graph.json' in low and any(word in {'test', '[', 'ls', 'stat'} for word in words))
    )

def extract_command_words(command: str) -> list:
    """Extract meaningful words from command."""
    try:
        lx = shlex.shlex(command, posix=True, punctuation_chars="|&;()")
        lx.whitespace_split = True
        tokens = list(lx)
    except ValueError:
        return []

    words = []
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
        words.append(word.lower())
        expect = False

    return words

def process_hook(data: dict) -> dict:
    """Main hook processing logic."""
    tool_input = data.get("tool_input", data)
    tool_name = data.get("tool_name", "Unknown")
    session = str(data.get("session_id") or "")

    log_debug(f"Processing tool: {tool_name}, session: {session[:20]}...")

    # Check bypass
    if BYPASS:
        log_debug("Bypass enabled, allowing all operations")
        return {}

    # Check if graphify exists
    exists = pathlib.Path("graphify-out/graph.json").exists()
    if not exists:
        log_debug("No graphify-out/graph.json found, allowing all")
        return {}

    decision = "allow"
    context_msg = None

    # Get context for better error messages
    context = get_context_from_tool_input(tool_input, tool_name)
    log_debug(f"Detected context: {context}")

    # Handle Grep tool - always block for exploration
    if tool_name == "Grep":
        decision = "deny"
        context_msg = format_error_message(
            "Grep is blocked for codebase exploration",
            context, tool_name
        )
        log_debug("Blocking Grep tool")

    # Handle Bash tool
    elif tool_name == "Bash":
        raw_command = str(tool_input.get("command", ""))

        # Check for graphify quota
        if is_graphify_call(raw_command):
            over_quota, count = check_quota(session)
            if over_quota:
                decision = "deny"
                context_msg = f"❌ BLOCKED: Maximum {QUOTA_LIMIT} Graphify discovery calls reached for this session.\n💡 TIP: Synthesize the answer from available context."
                log_debug(f"Quota exceeded: {count}/{QUOTA_LIMIT}")
            else:
                log_debug(f"Graphify call allowed: {count + 1}/{QUOTA_LIMIT}")

        # Check for probe commands
        elif is_probe_command(raw_command):
            decision = "deny"
            context_msg = format_error_message(
                "Probing graphify installation is blocked",
                context, tool_name
            )
            log_debug("Blocking probe command")

        # Check for blocked tools in command
        else:
            words = extract_command_words(raw_command)
            if any(word in BLOCKED_TOOLS for word in words):
                # Context-aware: allow if it's for debugging or building
                if context in {'debugging', 'building'}:
                    log_debug(f"Allowing {context} command: {raw_command[:50]}...")
                else:
                    decision = "deny"
                    context_msg = format_error_message(
                        "Search tools are blocked for codebase exploration",
                        context, tool_name
                    )
                    log_debug(f"Blocking command with search tools: {words}")

    # Handle Read/Glob tools
    elif tool_name in {"Read", "Glob"}:
        file_path = tool_input.get("file_path", "")
        if file_path:
            p = str(file_path).lower().replace("\\", "/")
            parts = set(pathlib.Path(p).parts)

            # Check if file is in ignored directories
            if not parts.intersection(IGNORED_DIRS):
                # Check if file has code extension
                if pathlib.Path(p).suffix in CODE_EXTENSIONS:
                    # Context-aware: allow if it's for editing or planning
                    if context in {'editing', 'planning'}:
                        log_debug(f"Allowing {context} read: {file_path}")
                    else:
                        decision = "deny"
                        context_msg = format_error_message(
                            "Reading source files for exploration is blocked",
                            context, tool_name, file_path
                        )
                        log_debug(f"Blocking read for exploration: {file_path}")

    # Build output
    out = {}
    if context_msg:
        out = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": context_msg
            }
        }
        if decision == "deny":
            out["hookSpecificOutput"].update({
                "permissionDecision": "deny",
                "permissionDecisionReason": context_msg
            })

    log_debug(f"Decision: {decision}, has context: {bool(context_msg)}")
    return out

def main():
    """Main entry point."""
    # Debug: Log that hook is being called
    log_debug("Hook script started")

    try:
        data = json.load(sys.stdin)
        log_debug(f"Received data: {json.dumps(data)[:200]}...")

        result = process_hook(data)
        log_debug(f"Result: {json.dumps(result)[:200]}...")

        sys.stdout.write(json.dumps(result) if result else "")
    except Exception as e:
        log_debug(f"Hook error: {e}")
        # On error, allow the operation (fail-open)
        sys.stdout.write("")

if __name__ == "__main__":
    main()
