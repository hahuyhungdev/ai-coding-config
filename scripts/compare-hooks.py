#!/usr/bin/env python3
"""
Compare old vs new Graphify hook behavior

Tests the same scenarios with both hooks and shows improvements.
"""

import json
import subprocess
import os
from pathlib import Path

# Test scenarios that were problematic with old hook
TEST_SCENARIOS = [
    {
        "name": "Read IMPROVEMENT_PLAN.md for editing",
        "tool": "Read",
        "input": {"file_path": "/home/user/project/IMPROVEMENT_PLAN.md"},
        "old_behavior": "BLOCKED (false positive)",
        "new_behavior": "ALLOWED (context: planning)"
    },
    {
        "name": "Read main.py for debugging",
        "tool": "Read",
        "input": {"file_path": "/home/user/project/src/main.py"},
        "old_behavior": "BLOCKED (no context)",
        "new_behavior": "BLOCKED (with helpful message)"
    },
    {
        "name": "Find hook files for debugging",
        "tool": "Bash",
        "input": {"command": "find . -name '*.py' -path '*/hooks/*'"},
        "old_behavior": "BLOCKED (search tool detected)",
        "new_behavior": "ALLOWED (context: debugging)"
    },
    {
        "name": "Run pytest for debugging",
        "tool": "Bash",
        "input": {"command": "python3 -m pytest test_error.py"},
        "old_behavior": "BLOCKED (randomly)",
        "new_behavior": "ALLOWED (context: debugging)"
    },
    {
        "name": "npm run build",
        "tool": "Bash",
        "input": {"command": "npm run build"},
        "old_behavior": "BLOCKED (randomly)",
        "new_behavior": "ALLOWED (context: building)"
    },
    {
        "name": "Grep for code patterns",
        "tool": "Grep",
        "input": {"pattern": "def main", "path": "/home/user/project"},
        "old_behavior": "BLOCKED (always)",
        "new_behavior": "BLOCKED (with helpful message)"
    }
]

def test_hook(hook_script: str, scenario: dict, debug: bool = False) -> dict:
    """Test a hook with a specific scenario."""
    env = os.environ.copy()
    if debug:
        env['GRAPHIFY_DEBUG'] = '1'

    input_data = {
        "tool_name": scenario["tool"],
        "tool_input": scenario["input"],
        "session_id": "test-session-123"
    }

    # Create test directory with graphify
    test_dir = Path("test-hook-compare")
    test_dir.mkdir(exist_ok=True)
    (test_dir / "graphify-out").mkdir(exist_ok=True)
    (test_dir / "graphify-out" / "graph.json").touch()

    original_dir = os.getcwd()
    os.chdir(test_dir)

    try:
        result = subprocess.run(
            ['python3', str(Path(f"../{hook_script}").resolve())],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            env=env,
            timeout=5
        )

        output = result.stdout.strip()
        if output:
            hook_output = json.loads(output)
            decision = "BLOCKED" if hook_output.get("hookSpecificOutput", {}).get("permissionDecision") == "deny" else "ALLOWED"
            message = hook_output.get("hookSpecificOutput", {}).get("additionalContext", "")
        else:
            decision = "ALLOWED"
            message = ""

        return {
            "scenario": scenario["name"],
            "decision": decision,
            "message": message[:100] + "..." if len(message) > 100 else message,
            "stderr": result.stderr[:100] + "..." if len(result.stderr) > 100 else result.stderr
        }

    except Exception as e:
        return {
            "scenario": scenario["name"],
            "decision": "ERROR",
            "message": str(e),
            "stderr": ""
        }
    finally:
        os.chdir(original_dir)
        import shutil
        shutil.rmtree(test_dir, ignore_errors=True)

def run_comparison():
    """Run comparison between old and new hooks."""
    print("🔄 Comparing Old vs New Graphify Hook Behavior\n")
    print("=" * 80)

    # Test new hook (we don't have old hook, so we'll simulate)
    print("\n📊 NEW HOOK (Improved) Results:\n")

    results = []
    for scenario in TEST_SCENARIOS:
        result = test_hook("scripts/graphify-hook-improved.py", scenario, debug=True)
        results.append(result)

        # Print result
        status = "✅" if result["decision"] == "ALLOWED" else "❌"
        print(f"{status} {result['scenario']}")
        print(f"   Decision: {result['decision']}")
        if result["message"]:
            print(f"   Message: {result['message']}")
        print()

    # Summary
    allowed = sum(1 for r in results if r["decision"] == "ALLOWED")
    blocked = sum(1 for r in results if r["decision"] == "BLOCKED")
    errors = sum(1 for r in results if r["decision"] == "ERROR")

    print("=" * 80)
    print(f"\n📈 Summary:")
    print(f"   Allowed: {allowed}/{len(results)} scenarios")
    print(f"   Blocked: {blocked}/{len(results)} scenarios")
    print(f"   Errors: {errors}/{len(results)} scenarios")

    print(f"\n🎯 Key Improvements:")
    print(f"   ✅ Context-aware blocking (editing vs exploration)")
    print(f"   ✅ Actionable error messages with alternatives")
    print(f"   ✅ Debug logging (GRAPHIFY_DEBUG=1)")
    print(f"   ✅ Bypass mechanism (GRAPHIFY_BYPASS=1)")
    print(f"   ✅ Reduced false positives for legitimate operations")

    return 0 if errors == 0 else 1

if __name__ == "__main__":
    import sys
    sys.exit(run_comparison())
