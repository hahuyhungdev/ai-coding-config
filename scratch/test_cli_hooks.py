#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
HOOK_SCRIPT = REPO_DIR / "claude" / "hooks" / "graphify_pre_tool.py"

def run_hook(client, tool, payload):
    cmd = [sys.executable, str(HOOK_SCRIPT), "--tool", tool, "--client", client]
    res = subprocess.run(
        cmd,
        input=json.dumps(payload),
        capture_output=True,
        text=True
    )
    return res.returncode, res.stdout, res.stderr

def main():
    print("Testing hook script:", HOOK_SCRIPT)
    print("=" * 60)

    # Make sure graphify-out/graph.json exists for tests to trigger blocking
    graph_dir = REPO_DIR / "graphify-out"
    graph_dir.mkdir(exist_ok=True)
    graph_json = graph_dir / "graph.json"
    if not graph_json.exists():
        graph_json.write_text("{}")
        created_graph = True
    else:
        created_graph = False

    try:
        # 1. Claude - Grep
        print("\nTest 1: Claude - Grep (Exploration)")
        payload = {"tool_input": {"pattern": "def setup_"}, "session_id": "test-session"}
        code, out, err = run_hook("claude", "Grep", payload)
        print(f"Exit Code: {code}")
        print(f"Stdout: {out}")
        if err: print(f"Stderr: {err}")
        assert "deny" in out
        assert "hookSpecificOutput" in out

        # 2. Claude - Bash (Normal command)
        print("\nTest 2: Claude - Bash (ls)")
        payload = {"tool_input": {"command": "ls"}, "session_id": "test-session"}
        code, out, err = run_hook("claude", "Bash", payload)
        print(f"Exit Code: {code}")
        print(f"Stdout: {out}")
        if err: print(f"Stderr: {err}")
        assert out.strip() == ""

        # 3. Claude - Read (Exploration)
        print("\nTest 3: Claude - Read (Exploration)")
        payload = {"tool_input": {"file_path": "install.py"}, "session_id": "test-session"}
        code, out, err = run_hook("claude", "Read", payload)
        print(f"Exit Code: {code}")
        print(f"Stdout: {out}")
        if err: print(f"Stderr: {err}")
        assert "deny" in out

        # 4. Gemini - Grep
        print("\nTest 4: Gemini - Grep (Exploration)")
        payload = {"tool_input": {"pattern": "def setup_"}, "session_id": "test-session"}
        code, out, err = run_hook("gemini", "Grep", payload)
        print(f"Exit Code: {code}")
        print(f"Stdout: {out}")
        if err: print(f"Stderr: {err}")
        assert "deny" in out
        assert "decision" in out

        # 5. Gemini - Bash (Normal command)
        print("\nTest 5: Gemini - Bash (ls)")
        payload = {"tool_input": {"command": "ls"}, "session_id": "test-session"}
        code, out, err = run_hook("gemini", "Bash", payload)
        print(f"Exit Code: {code}")
        print(f"Stdout: {out}")
        if err: print(f"Stderr: {err}")
        data = json.loads(out)
        assert data.get("decision") == "allow"

        # 6. Gemini - Read (Exploration)
        print("\nTest 6: Gemini - Read (Exploration)")
        payload = {"tool_input": {"file_path": "install.py"}, "session_id": "test-session"}
        code, out, err = run_hook("gemini", "Read", payload)
        print(f"Exit Code: {code}")
        print(f"Stdout: {out}")
        if err: print(f"Stderr: {err}")
        assert "deny" in out

        print("\n" + "=" * 60)
        print("🎉 All test scenarios passed successfully!")

    finally:
        # Clean up temporary graph.json if we created it
        if created_graph and graph_json.exists():
            graph_json.unlink()

if __name__ == "__main__":
    main()
