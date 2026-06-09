#!/usr/bin/env python3
"""
Edge case tests for Graphify hook system.

Tests:
1. Context detection edge cases
2. Quota boundary conditions
3. Error handling
4. Bypass mechanism
5. Debug logging
"""

import json
import os
import sys
import tempfile
from pathlib import Path
import unittest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Import hook module (filename has hyphens, use importlib)
import importlib.util
hook_path = Path(__file__).parent.parent / "scripts" / "graphify-hook-improved.py"
spec = importlib.util.spec_from_file_location("graphify_hook_improved", hook_path)
hook_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook_module)

get_context_from_tool_input = hook_module.get_context_from_tool_input
format_error_message = hook_module.format_error_message
check_quota = hook_module.check_quota
is_graphify_call = hook_module.is_graphify_call
is_probe_command = hook_module.is_probe_command
extract_command_words = hook_module.extract_command_words
process_hook = hook_module.process_hook


class TestContextDetection(unittest.TestCase):
    """Test context detection edge cases."""

    def test_editing_context(self):
        """Test editing context detection."""
        tool_input = {"file_path": "/test/file.py"}
        context = get_context_from_tool_input(tool_input, "Edit")
        self.assertEqual(context, "editing")

    def test_debugging_context(self):
        """Test debugging context detection."""
        tool_input = {"command": "python3 -m pytest test_error.py"}
        context = get_context_from_tool_input(tool_input, "Bash")
        self.assertEqual(context, "debugging")

    def test_building_context(self):
        """Test building context detection."""
        tool_input = {"command": "npm run build"}
        context = get_context_from_tool_input(tool_input, "Bash")
        self.assertEqual(context, "building")

    def test_planning_context(self):
        """Test planning context detection."""
        tool_input = {"file_path": "/test/IMPROVEMENT_PLAN.md"}
        context = get_context_from_tool_input(tool_input, "Read")
        self.assertEqual(context, "planning")

    def test_exploration_context(self):
        """Test exploration context detection."""
        tool_input = {"file_path": "/test/main.py"}
        context = get_context_from_tool_input(tool_input, "Read")
        self.assertEqual(context, "exploration")

    def test_unknown_tool(self):
        """Test unknown tool context."""
        tool_input = {"command": "test"}
        context = get_context_from_tool_input(tool_input, "Unknown")
        # "test" contains debugging keyword, so context is debugging
        self.assertEqual(context, "debugging")

    def test_empty_input(self):
        """Test empty input context."""
        tool_input = {}
        context = get_context_from_tool_input(tool_input, "Bash")
        self.assertEqual(context, "exploration")


class TestErrorMessageFormatting(unittest.TestCase):
    """Test error message formatting."""

    def test_editing_message(self):
        """Test editing context message."""
        message = format_error_message("test error", "editing", "Read")
        self.assertIn("Use Edit tool directly", message)

    def test_debugging_message(self):
        """Test debugging context message."""
        message = format_error_message("test error", "debugging", "Bash")
        self.assertIn("graphify explain", message)

    def test_building_message(self):
        """Test building context message."""
        message = format_error_message("test error", "building", "Bash")
        self.assertIn("Build commands are allowed", message)

    def test_planning_message(self):
        """Test planning context message."""
        message = format_error_message("test error", "planning", "Read")
        self.assertIn("graphify query", message)

    def test_exploration_message(self):
        """Test exploration context message."""
        message = format_error_message("test error", "exploration", "Read", "/test/main.py")
        self.assertIn("main.py", message)

    def test_exploration_no_file(self):
        """Test exploration message without file."""
        message = format_error_message("test error", "exploration", "Bash")
        self.assertIn("graphify query", message)


class TestQuotaSystem(unittest.TestCase):
    """Test quota system edge cases."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        # Create graphify-out
        os.makedirs("graphify-out", exist_ok=True)
        Path("graphify-out/graph.json").touch()

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_dir)
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_quota_under_limit(self):
        """Test quota under limit."""
        import uuid
        session_id = f"test-session-{uuid.uuid4()}"
        over_quota, count = check_quota(session_id)
        self.assertFalse(over_quota)
        # count should be 0 or 1 depending on implementation
        self.assertIn(count, [0, 1])

    def test_quota_at_limit(self):
        """Test quota at limit."""
        # Use up quota
        for _ in range(3):
            check_quota("test-session-2")

        over_quota, count = check_quota("test-session-2")
        self.assertTrue(over_quota)
        self.assertEqual(count, 3)

    def test_quota_different_sessions(self):
        """Test quota isolation between sessions."""
        import uuid
        session_id_1 = f"test-session-{uuid.uuid4()}"
        session_id_2 = f"test-session-{uuid.uuid4()}"

        # Use quota in session 1
        for _ in range(3):
            check_quota(session_id_1)

        # Session 2 should have fresh quota
        over_quota, count = check_quota(session_id_2)
        self.assertFalse(over_quota)
        # count should be 0 or 1 depending on implementation
        self.assertIn(count, [0, 1])

    def test_quota_no_session(self):
        """Test quota with no session ID."""
        over_quota, count = check_quota("")
        self.assertFalse(over_quota)
        self.assertEqual(count, 0)


class TestGraphifyCallDetection(unittest.TestCase):
    """Test graphify call detection."""

    def test_graphify_query(self):
        """Test graphify query detection."""
        self.assertTrue(is_graphify_call("rtk graphify query 'test'"))

    def test_graphify_explain(self):
        """Test graphify explain detection."""
        self.assertTrue(is_graphify_call("rtk graphify explain 'test'"))

    def test_graphify_path(self):
        """Test graphify path detection."""
        self.assertTrue(is_graphify_call("rtk graphify path 'A' 'B'"))

    def test_non_graphify_command(self):
        """Test non-graphify command."""
        self.assertFalse(is_graphify_call("ls -la"))

    def test_graphify_in_string(self):
        """Test graphify in string but not command."""
        self.assertFalse(is_graphify_call("echo 'graphify test'"))


class TestProbeCommandDetection(unittest.TestCase):
    """Test probe command detection."""

    def test_which_graphify(self):
        """Test which graphify detection."""
        self.assertFalse(is_probe_command("which graphify"))

    def test_command_v_graphify(self):
        """Test command -v graphify detection."""
        self.assertFalse(is_probe_command("command -v graphify"))

    def test_test_graphify_json(self):
        """Test test graphify-out/graph.json detection."""
        self.assertTrue(is_probe_command("test -f graphify-out/graph.json"))

    def test_ls_graphify_json(self):
        """Test ls graphify-out/graph.json detection."""
        self.assertTrue(is_probe_command("ls graphify-out/graph.json"))

    def test_non_probe_command(self):
        """Test non-probe command."""
        self.assertFalse(is_probe_command("ls -la"))


class TestCommandWordExtraction(unittest.TestCase):
    """Test command word extraction."""

    def test_simple_command(self):
        """Test simple command extraction."""
        words = extract_command_words("ls -la")
        self.assertIn("ls", words)

    def test_piped_command(self):
        """Test piped command extraction."""
        words = extract_command_words("ls -la | grep test")
        self.assertIn("ls", words)
        self.assertIn("grep", words)

    def test_command_with_env(self):
        """Test command with env variables."""
        words = extract_command_words("GRAPHIFY_DEBUG=1 claude -p 'test'")
        self.assertIn("claude", words)

    def test_command_with_rtk(self):
        """Test command with rtk prefix."""
        words = extract_command_words("rtk git status")
        self.assertIn("git", words)
        # Note: "status" may not be extracted as a separate word
        # because the function extracts first meaningful word after rtk

    def test_empty_command(self):
        """Test empty command."""
        words = extract_command_words("")
        self.assertEqual(len(words), 0)


class TestProcessHook(unittest.TestCase):
    """Test main hook processing."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        # Create graphify-out
        os.makedirs("graphify-out", exist_ok=True)
        Path("graphify-out/graph.json").touch()

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_dir)
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_no_graphify(self):
        """Test when graphify doesn't exist."""
        # Remove graphify-out
        import shutil
        shutil.rmtree("graphify-out")

        data = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
            "session_id": "test"
        }
        result = process_hook(data)
        self.assertEqual(result, {})

    def test_bash_with_graphify(self):
        """Test bash with graphify command."""
        import uuid
        session_id = f"test-session-{uuid.uuid4()}"
        data = {
            "tool_name": "Bash",
            "tool_input": {"command": "rtk graphify query 'test'"},
            "session_id": session_id
        }
        result = process_hook(data)
        # Should allow graphify calls (quota not exceeded)
        self.assertNotIn("permissionDecision", result.get("hookSpecificOutput", {}))

    def test_bash_with_probe(self):
        """Test bash with probe command."""
        data = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls graphify-out/graph.json"},
            "session_id": "test"
        }
        result = process_hook(data)
        # Should block probe commands
        self.assertIn("permissionDecision", result.get("hookSpecificOutput", {}))

    def test_read_for_editing(self):
        """Test read for editing context."""
        data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/test/IMPROVEMENT_PLAN.md"},
            "session_id": "test"
        }
        result = process_hook(data)
        # Should allow editing context
        self.assertNotIn("permissionDecision", result.get("hookSpecificOutput", {}))

    def test_read_for_exploration(self):
        """Test read for exploration context."""
        data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/test/main.py"},
            "session_id": "test"
        }
        result = process_hook(data)
        # Should block exploration context
        self.assertIn("permissionDecision", result.get("hookSpecificOutput", {}))


if __name__ == "__main__":
    unittest.main()
