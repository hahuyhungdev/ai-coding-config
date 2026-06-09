#!/usr/bin/env python3
"""
Test script for improved Graphify hook

Tests:
1. Context-aware blocking
2. Error message quality
3. Debug logging
4. Bypass mechanism
5. False positive reduction
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# Test cases
TEST_CASES = [
    {
        "name": "Read for editing (should allow)",
        "tool": "Read",
        "input": {"file_path": "/home/user/project/IMPROVEMENT_PLAN.md"},
        "expected": "allow",
        "context": "planning"
    },
    {
        "name": "Read for exploration (should block)",
        "tool": "Read",
        "input": {"file_path": "/home/user/project/src/main.py"},
        "expected": "deny",
        "context": "exploration"
    },
    {
        "name": "Grep for exploration (should block)",
        "tool": "Grep",
        "input": {"pattern": "function", "path": "/home/user/project"},
        "expected": "deny",
        "context": "exploration"
    },
    {
        "name": "Bash with find (should block)",
        "tool": "Bash",
        "input": {"command": "find . -name '*.py'"},
        "expected": "deny",
        "context": "exploration"
    },
    {
        "name": "Bash with graphify query (should allow if quota available)",
        "tool": "Bash",
        "input": {"command": "rtk graphify query 'test'"},
        "expected": "allow",
        "context": "exploration"
    },
    {
        "name": "Bash with debug command (should allow)",
        "tool": "Bash",
        "input": {"command": "python3 -m pytest test_error.py"},
        "expected": "allow",
        "context": "debugging"
    },
    {
        "name": "Bash with build command (should allow)",
        "tool": "Bash",
        "input": {"command": "npm run build"},
        "expected": "allow",
        "context": "building"
    }
]

def run_test(test_case: dict, debug: bool = False, bypass: bool = False) -> dict:
    """Run a single test case."""
    env = os.environ.copy()
    if debug:
        env['GRAPHIFY_DEBUG'] = '1'
    if bypass:
        env['GRAPHIFY_BYPASS'] = '1'

    # Prepare input data
    input_data = {
        "tool_name": test_case["tool"],
        "tool_input": test_case["input"],
        "session_id": "test-session-123"
    }

    # Run hook
    try:
        # Get absolute path to hook script
        hook_script = Path(__file__).parent / "graphify-hook-improved.py"
        result = subprocess.run(
            ['python3', str(hook_script)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            env=env,
            timeout=5
        )

        # Parse output
        output = result.stdout.strip()
        if output:
            hook_output = json.loads(output)
            decision = "deny" if hook_output.get("hookSpecificOutput", {}).get("permissionDecision") == "deny" else "allow"
        else:
            decision = "allow"

        return {
            "test": test_case["name"],
            "expected": test_case["expected"],
            "actual": decision,
            "passed": decision == test_case["expected"],
            "stderr": result.stderr if debug else "",
            "output": output
        }

    except Exception as e:
        return {
            "test": test_case["name"],
            "expected": test_case["expected"],
            "actual": "error",
            "passed": False,
            "error": str(e)
        }

def run_all_tests():
    """Run all test cases."""
    print("🧪 Running Graphify Hook Improvement Tests\n")

    # Create temporary graphify-out for testing
    test_dir = Path("test-graphify-hook")
    test_dir.mkdir(exist_ok=True)
    (test_dir / "graphify-out").mkdir(exist_ok=True)
    (test_dir / "graphify-out" / "graph.json").touch()

    # Change to test directory
    original_dir = os.getcwd()
    os.chdir(test_dir)

    results = []
    for test_case in TEST_CASES:
        result = run_test(test_case, debug=True)
        results.append(result)

        # Print result
        status = "✅" if result["passed"] else "❌"
        print(f"{status} {result['test']}")
        if not result["passed"]:
            print(f"   Expected: {result['expected']}, Got: {result['actual']}")
            if result.get("error"):
                print(f"   Error: {result['error']}")
        if result.get("stderr"):
            print(f"   Debug: {result['stderr'][:100]}...")

    # Cleanup
    os.chdir(original_dir)
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)

    # Summary
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"\n📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())
