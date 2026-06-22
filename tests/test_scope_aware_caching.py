"""Comprehensive tests for scope-aware caching and minified instructions.

Covers the new helper functions in graphify_pre_tool.py and end-to-end
scenarios that exercise the scope-aware blocking/allowing pipeline via
real subprocess calls to the hook classifier script.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock


# ---------------------------------------------------------------------------
# Module-level import of graphify_pre_tool helper functions
# ---------------------------------------------------------------------------

_HOOK_MODULE_PATH = str(Path(__file__).parent.parent / "claude" / "hooks" / "graphify_pre_tool.py")


def _load_hook_module():
    """Import graphify_pre_tool.py as a module for unit testing helper functions."""
    spec = importlib.util.spec_from_file_location("graphify_pre_tool", _HOOK_MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_hook_mod = _load_hook_module()


# ---------------------------------------------------------------------------
# Helper: run the hook classifier script as a subprocess (mirrors real agy CLI)
# ---------------------------------------------------------------------------

def _run_hook(tool_name, payload, *, cwd=None, env=None):
    """Execute the hook classifier subprocess and return parsed output.

    Uses the _hook_classifier_script() from installer_graphify to generate
    the exact script that agy CLI would run, then feeds it JSON via stdin —
    matching the real-world invocation path.
    """
    from installer_graphify import _hook_classifier_script
    script = _hook_classifier_script(tool_name, True)  # Claude mode
    result = subprocess.run(
        args=[sys.executable, "-c", script],
        cwd=cwd or tempfile.gettempdir(),
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    stdout = result.stdout.strip()
    if not stdout:
        return None  # "allow" with no output
    return json.loads(stdout)


def _make_project(base_dir, name="project"):
    """Create a temp project directory with graphify-out/graph.json."""
    project = Path(base_dir) / name
    project.mkdir(parents=True, exist_ok=True)
    (project / "graphify-out").mkdir(exist_ok=True)
    (project / "graphify-out" / "graph.json").write_text("{}")
    return project


def _cleanup_session_files(session_id):
    """Clean up temp state files for a session."""
    safe = "".join(ch for ch in session_id if ch.isalnum() or ch in "-_")[:120]
    for pattern in [
        f"ai-coding-config-graphify-{safe}.count",
        f"ai-coding-config-graphify-scopes-{safe}.json",
    ]:
        p = Path(tempfile.gettempdir()) / pattern
        if p.exists():
            p.unlink()


# ===========================================================================
# Unit Tests: extract_graphify_scope
# ===========================================================================

class TestExtractGraphifyScope(unittest.TestCase):
    """Test scope extraction from various graphify command patterns."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.project = _make_project(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_query_command_returns_cwd_scope(self):
        """A simple 'graphify query' should resolve scope to cwd (which has graphify-out)."""
        scope = _hook_mod.extract_graphify_scope(
            "rtk graphify query 'architecture'", str(self.project)
        )
        self.assertEqual(scope, str(self.project))

    def test_update_command_returns_target_dir(self):
        """'graphify update .' should return the resolved target directory."""
        scope = _hook_mod.extract_graphify_scope(
            "rtk graphify update .", str(self.project)
        )
        # "." resolves to project dir
        self.assertEqual(scope, str(self.project.resolve()))

    def test_update_with_explicit_subdir(self):
        """'graphify update src/' should return the resolved src/ directory."""
        src = self.project / "src"
        src.mkdir(exist_ok=True)
        scope = _hook_mod.extract_graphify_scope(
            "rtk graphify update src/", str(self.project)
        )
        self.assertEqual(scope, str(src.resolve()))

    def test_graph_flag_extracts_parent_of_graphify_out(self):
        """'--graph graphify-out/graph.json' should return parent of graphify-out."""
        scope = _hook_mod.extract_graphify_scope(
            "rtk graphify query 'x' --graph graphify-out/graph.json", str(self.project)
        )
        self.assertEqual(scope, str(self.project.resolve()))

    def test_extract_subcommand_with_dir(self):
        """'graphify extract /some/path' should use the path argument."""
        target = self.project / "libs"
        target.mkdir(exist_ok=True)
        scope = _hook_mod.extract_graphify_scope(
            f"rtk graphify extract {target}", str(self.project)
        )
        self.assertEqual(scope, str(target.resolve()))

    def test_no_subcommand_falls_back_to_cwd_graphify_parent(self):
        """When no subcommand is recognized, falls back to graphify-out parent scan."""
        scope = _hook_mod.extract_graphify_scope(
            "echo hello", str(self.project)
        )
        # Falls through all checks but finds graphify-out/graph.json in project dir
        self.assertEqual(scope, str(self.project.resolve()))


# ===========================================================================
# Unit Tests: add_allowed_scope / get_allowed_scopes
# ===========================================================================

class TestAllowedScopes(unittest.TestCase):
    """Test scope state management (add/get)."""

    def setUp(self):
        self.session = f"test-scopes-{uuid.uuid4()}"

    def tearDown(self):
        _cleanup_session_files(self.session)

    def test_get_returns_empty_when_no_state(self):
        scopes = _hook_mod.get_allowed_scopes(self.session)
        self.assertEqual(scopes, [])

    def test_add_then_get_returns_scope(self):
        _hook_mod.add_allowed_scope(self.session, "/home/user/project-a")
        scopes = _hook_mod.get_allowed_scopes(self.session)
        self.assertIn(str(Path("/home/user/project-a").resolve()), scopes)

    def test_add_duplicate_scope_is_idempotent(self):
        _hook_mod.add_allowed_scope(self.session, "/home/user/project-a")
        _hook_mod.add_allowed_scope(self.session, "/home/user/project-a")
        scopes = _hook_mod.get_allowed_scopes(self.session)
        resolved = str(Path("/home/user/project-a").resolve())
        self.assertEqual(scopes.count(resolved), 1)

    def test_add_multiple_distinct_scopes(self):
        _hook_mod.add_allowed_scope(self.session, "/home/user/project-a")
        _hook_mod.add_allowed_scope(self.session, "/home/user/project-b")
        scopes = _hook_mod.get_allowed_scopes(self.session)
        self.assertEqual(len(scopes), 2)

    def test_empty_session_returns_empty(self):
        self.assertEqual(_hook_mod.get_allowed_scopes(""), [])
        self.assertEqual(_hook_mod.get_allowed_scopes(None), [])

    def test_add_with_empty_session_is_noop(self):
        _hook_mod.add_allowed_scope("", "/some/path")
        _hook_mod.add_allowed_scope(None, "/some/path")
        # Should not crash

    def test_add_with_empty_path_is_noop(self):
        _hook_mod.add_allowed_scope(self.session, "")
        _hook_mod.add_allowed_scope(self.session, None)
        scopes = _hook_mod.get_allowed_scopes(self.session)
        self.assertEqual(scopes, [])

    def test_session_isolation(self):
        """Different sessions should have isolated scopes."""
        session2 = f"test-scopes-other-{uuid.uuid4()}"
        try:
            _hook_mod.add_allowed_scope(self.session, "/home/user/project-a")
            _hook_mod.add_allowed_scope(session2, "/home/user/project-b")
            scopes_1 = _hook_mod.get_allowed_scopes(self.session)
            scopes_2 = _hook_mod.get_allowed_scopes(session2)
            self.assertEqual(len(scopes_1), 1)
            self.assertEqual(len(scopes_2), 1)
            self.assertNotEqual(scopes_1, scopes_2)
        finally:
            _cleanup_session_files(session2)


# ===========================================================================
# Unit Tests: is_path_in_allowed_scopes
# ===========================================================================

class TestIsPathInAllowedScopes(unittest.TestCase):
    """Test path-scope matching logic."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_file_under_scope_is_allowed(self):
        scope = str(Path(self.tmp).resolve())
        target = str(Path(self.tmp) / "src" / "main.py")
        self.assertTrue(_hook_mod.is_path_in_allowed_scopes(target, [scope]))

    def test_file_outside_scope_is_denied(self):
        scope = str(Path(self.tmp) / "project-a")
        target = str(Path(self.tmp) / "project-b" / "main.py")
        self.assertFalse(_hook_mod.is_path_in_allowed_scopes(target, [scope]))

    def test_exact_scope_path_matches(self):
        scope = str(Path(self.tmp).resolve())
        self.assertTrue(_hook_mod.is_path_in_allowed_scopes(scope, [scope]))

    def test_empty_scopes_returns_false(self):
        self.assertFalse(_hook_mod.is_path_in_allowed_scopes("/any/path", []))

    def test_none_scopes_returns_false(self):
        self.assertFalse(_hook_mod.is_path_in_allowed_scopes("/any/path", None))

    def test_multiple_scopes_matches_any(self):
        scope_a = str(Path(self.tmp) / "a")
        scope_b = str(Path(self.tmp) / "b")
        target = str(Path(self.tmp) / "b" / "src" / "file.py")
        Path(self.tmp, "a").mkdir()
        Path(self.tmp, "b", "src").mkdir(parents=True)
        self.assertTrue(_hook_mod.is_path_in_allowed_scopes(target, [scope_a, scope_b]))

    def test_nested_scope_allows_deeper_files(self):
        scope = str(Path(self.tmp) / "project" / "src")
        target = str(Path(self.tmp) / "project" / "src" / "utils" / "helper.py")
        self.assertTrue(_hook_mod.is_path_in_allowed_scopes(target, [scope]))

    def test_sibling_directory_not_allowed(self):
        scope = str(Path(self.tmp) / "project" / "src")
        target = str(Path(self.tmp) / "project" / "tests" / "test.py")
        self.assertFalse(_hook_mod.is_path_in_allowed_scopes(target, [scope]))


# ===========================================================================
# Unit Tests: is_system_or_temp_path
# ===========================================================================

class TestIsSystemOrTempPath(unittest.TestCase):
    """Test identification of system/temp paths."""

    def test_temp_dir_is_detected(self):
        temp = Path(tempfile.gettempdir()) / "some_file.py"
        self.assertTrue(_hook_mod.is_system_or_temp_path(temp.resolve()))

    def test_tmp_in_path_is_detected(self):
        p = Path("/tmp/some_project/file.py")
        self.assertTrue(_hook_mod.is_system_or_temp_path(p))

    def test_system_dirs_are_detected(self):
        for d in ["/usr/lib/python3/file.py", "/etc/config.py", "/var/log/app.py",
                   "/proc/self/status", "/sys/class/net", "/opt/app/main.py"]:
            with self.subTest(d=d):
                self.assertTrue(_hook_mod.is_system_or_temp_path(Path(d)))

    def test_user_project_is_not_system(self):
        p = Path("/home/user/projects/myapp/src/main.py")
        self.assertFalse(_hook_mod.is_system_or_temp_path(p))

    def test_graphify_project_in_tmp_is_not_system(self):
        """A temp dir containing graphify-out/graph.json should NOT be flagged."""
        tmp = tempfile.mkdtemp()
        try:
            (Path(tmp) / "graphify-out").mkdir()
            (Path(tmp) / "graphify-out" / "graph.json").write_text("{}")
            target = Path(tmp) / "src" / "main.py"
            # The function checks parents for graphify-out/graph.json
            self.assertFalse(_hook_mod.is_system_or_temp_path(target.resolve()))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_dev_path_is_system(self):
        self.assertTrue(_hook_mod.is_system_or_temp_path(Path("/dev/null")))

    def test_lib64_is_system(self):
        self.assertTrue(_hook_mod.is_system_or_temp_path(Path("/lib64/libm.so")))


# ===========================================================================
# Unit Tests: extract_paths_from_input
# ===========================================================================

class TestExtractPathsFromInput(unittest.TestCase):
    """Test path extraction from tool input dictionaries."""

    def test_absolute_path_field(self):
        paths = _hook_mod.extract_paths_from_input({"AbsolutePath": "/home/user/file.py"})
        self.assertEqual(paths, ["/home/user/file.py"])

    def test_directory_path_field(self):
        paths = _hook_mod.extract_paths_from_input({"DirectoryPath": "/home/user/src"})
        self.assertEqual(paths, ["/home/user/src"])

    def test_search_path_field(self):
        paths = _hook_mod.extract_paths_from_input({"SearchPath": "/home/user/project"})
        self.assertEqual(paths, ["/home/user/project"])

    def test_file_path_field(self):
        paths = _hook_mod.extract_paths_from_input({"file_path": "src/main.py"})
        self.assertEqual(paths, ["src/main.py"])

    def test_multiple_fields(self):
        paths = _hook_mod.extract_paths_from_input({
            "file_path": "a.py",
            "path": "b/",
        })
        self.assertEqual(len(paths), 2)

    def test_empty_input(self):
        paths = _hook_mod.extract_paths_from_input({})
        self.assertEqual(paths, [])

    def test_none_values_ignored(self):
        paths = _hook_mod.extract_paths_from_input({"file_path": None, "path": None})
        self.assertEqual(paths, [])


# ===========================================================================
# Unit Tests: extract_paths_from_command
# ===========================================================================

class TestExtractPathsFromCommand(unittest.TestCase):
    """Test path extraction from shell commands."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Create some files for matching
        (Path(self.tmp) / "main.py").write_text("pass")
        (Path(self.tmp) / "src").mkdir()
        (Path(self.tmp) / "src" / "app.ts").write_text("//")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cat_with_existing_file(self):
        paths = _hook_mod.extract_paths_from_command("cat main.py", self.tmp)
        self.assertTrue(any("main.py" in p for p in paths))

    def test_flags_are_skipped(self):
        paths = _hook_mod.extract_paths_from_command("cat -n --number main.py", self.tmp)
        # Should not include -n or --number
        self.assertTrue(all(not p.startswith("-") for p in paths))

    def test_file_with_known_extension(self):
        paths = _hook_mod.extract_paths_from_command("cat unknown_file.py", self.tmp)
        # .py is in E so it should be extracted even if file doesn't exist
        self.assertTrue(any("unknown_file.py" in p for p in paths))

    def test_command_with_no_path_args(self):
        paths = _hook_mod.extract_paths_from_command("echo hello world", self.tmp)
        self.assertEqual(paths, [])

    def test_invalid_command_string(self):
        paths = _hook_mod.extract_paths_from_command("", self.tmp)
        self.assertEqual(paths, [])


# ===========================================================================
# End-to-End: Scope-Aware Caching via Subprocess
# ===========================================================================

class TestScopeAwareCachingE2E(unittest.TestCase):
    """End-to-end tests that run the hook as a subprocess, mimicking the
    real agy CLI invocation path."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.project_a = _make_project(self.tmp, "project-a")
        self.project_b = _make_project(self.tmp, "project-b")
        self.session = f"e2e-scope-{uuid.uuid4()}"

        # Create source files
        (self.project_a / "src").mkdir()
        (self.project_a / "src" / "main.py").write_text("print('A')")
        (self.project_b / "src").mkdir()
        (self.project_b / "src" / "main.py").write_text("print('B')")

    def tearDown(self):
        _cleanup_session_files(self.session)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_read_before_graphify_is_denied(self):
        """Reading a source file before running any graphify query should be denied."""
        result = _run_hook("Read", {
            "conversationId": self.session,
            "tool_input": {
                "AbsolutePath": str(self.project_a / "src" / "main.py"),
                "toolAction": "Exploring codebase",
            },
            "cwd": str(self.project_a),
        }, cwd=self.project_a)
        self.assertIsNotNone(result)
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_graphify_query_then_read_in_same_project_allowed(self):
        """After graphify query in project A, reads within A should be allowed."""
        # Run graphify query first
        _run_hook("Bash", {
            "conversationId": self.session,
            "tool_input": {"command": "rtk graphify query 'architecture'"},
            "cwd": str(self.project_a),
        }, cwd=self.project_a)

        # Now read in same project — should be allowed
        result = _run_hook("Read", {
            "conversationId": self.session,
            "tool_input": {
                "AbsolutePath": str(self.project_a / "src" / "main.py"),
                "toolAction": "Exploring codebase",
            },
            "cwd": str(self.project_a),
        }, cwd=self.project_a)
        self.assertIsNone(result)  # None = allowed (empty output)

    def test_graphify_in_project_a_blocks_reads_in_project_b(self):
        """After graphify query in project A, reads in project B should be blocked."""
        _run_hook("Bash", {
            "conversationId": self.session,
            "tool_input": {"command": "rtk graphify query 'architecture'"},
            "cwd": str(self.project_a),
        }, cwd=self.project_a)

        result = _run_hook("Read", {
            "conversationId": self.session,
            "tool_input": {
                "AbsolutePath": str(self.project_b / "src" / "main.py"),
                "toolAction": "Exploring codebase",
            },
            "cwd": str(self.project_a),
        }, cwd=self.project_a)
        self.assertIsNotNone(result)
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("outside the explored Graphify scope", result["hookSpecificOutput"]["permissionDecisionReason"])

    def test_graphify_in_both_projects_allows_reads_in_both(self):
        """Running graphify in both projects should allow reads in both."""
        for proj in (self.project_a, self.project_b):
            _run_hook("Bash", {
                "conversationId": self.session,
                "tool_input": {"command": "rtk graphify query 'overview'"},
                "cwd": str(proj),
            }, cwd=proj)

        # Both should be allowed
        for proj in (self.project_a, self.project_b):
            result = _run_hook("Read", {
                "conversationId": self.session,
                "tool_input": {
                    "AbsolutePath": str(proj / "src" / "main.py"),
                    "toolAction": "Exploring codebase",
                },
                "cwd": str(proj),
            }, cwd=proj)
            self.assertIsNone(result, f"Read in {proj.name} should be allowed")

    def test_config_files_bypass_scope_check(self):
        """Config/doc files (.json, .md, .yaml, etc.) bypass scope-aware blocking."""
        _run_hook("Bash", {
            "conversationId": self.session,
            "tool_input": {"command": "rtk graphify query 'overview'"},
            "cwd": str(self.project_a),
        }, cwd=self.project_a)

        # Read .json in project_b — should be allowed (config bypass)
        config_file = self.project_b / "package.json"
        config_file.write_text('{"name": "test"}')
        result = _run_hook("Read", {
            "conversationId": self.session,
            "tool_input": {
                "AbsolutePath": str(config_file),
                "toolAction": "Exploring codebase",
            },
            "cwd": str(self.project_a),
        }, cwd=self.project_a)
        # Config files (.json) are excluded from scope-aware blocking
        self.assertIsNone(result)

    def test_markdown_files_bypass_scope_check(self):
        """Markdown files should bypass scope-aware blocking."""
        _run_hook("Bash", {
            "conversationId": self.session,
            "tool_input": {"command": "rtk graphify query 'overview'"},
            "cwd": str(self.project_a),
        }, cwd=self.project_a)

        md_file = self.project_b / "README.md"
        md_file.write_text("# Test")
        result = _run_hook("Read", {
            "conversationId": self.session,
            "tool_input": {
                "AbsolutePath": str(md_file),
                "toolAction": "Exploring codebase",
            },
            "cwd": str(self.project_a),
        }, cwd=self.project_a)
        self.assertIsNone(result)

    def test_edit_tool_bypasses_read_block(self):
        """The Edit tool gets tool_ctx='editing', bypassing exploration blocks.
        Note: Read tool always gets tool_ctx='exploration' regardless of
        toolAction — the editing bypass only applies to Edit tool."""
        result = _run_hook("Edit", {
            "conversationId": self.session,
            "tool_input": {
                "file_path": str(self.project_a / "src" / "main.py"),
                "ReplacementChunks": [],
            },
            "cwd": str(self.project_a),
        }, cwd=self.project_a)
        # Edit tool is always allowed (tool_ctx = "editing")
        self.assertIsNone(result)

    def test_read_tool_is_always_exploration_context(self):
        """Read tool always gets tool_ctx='exploration', even with toolAction
        containing 'editing' or 'debugging'. This means Read is always
        subject to g_count and scope checks."""
        result = _run_hook("Read", {
            "conversationId": self.session,
            "tool_input": {
                "AbsolutePath": str(self.project_a / "src" / "main.py"),
                "toolAction": "Editing file",
            },
            "cwd": str(self.project_a),
        }, cwd=self.project_a)
        # Read tool with g_count==0 is denied regardless of toolAction
        self.assertIsNotNone(result)
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_bash_debug_command_bypasses_exploration_block(self):
        """Bash commands with debug/test keywords get tool_ctx='debugging',
        bypassing the exploration read block."""
        result = _run_hook("Bash", {
            "conversationId": self.session,
            "tool_input": {
                "command": "pytest tests/test_main.py",
            },
            "cwd": str(self.project_a),
        }, cwd=self.project_a)
        self.assertIsNone(result)

    def test_exploration_context_triggers_scope_check(self):
        """Explicitly verify that 'exploration' context triggers scope-aware blocking."""
        _run_hook("Bash", {
            "conversationId": self.session,
            "tool_input": {"command": "rtk graphify query 'overview'"},
            "cwd": str(self.project_a),
        }, cwd=self.project_a)

        # "exploration" context + out-of-scope path => blocked
        result = _run_hook("Read", {
            "conversationId": self.session,
            "tool_input": {
                "AbsolutePath": str(self.project_b / "src" / "main.py"),
                "toolAction": "Exploring codebase",
            },
            "cwd": str(self.project_a),
        }, cwd=self.project_a)
        self.assertIsNotNone(result)
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_glob_tool_respects_scope(self):
        """Glob tool should also be subject to scope-aware blocking."""
        _run_hook("Bash", {
            "conversationId": self.session,
            "tool_input": {"command": "rtk graphify query 'overview'"},
            "cwd": str(self.project_a),
        }, cwd=self.project_a)

        result = _run_hook("Glob", {
            "conversationId": self.session,
            "tool_input": {
                "path": str(self.project_b / "src"),
                "pattern": "*.py",
                "toolAction": "Exploring codebase",
            },
            "cwd": str(self.project_a),
        }, cwd=self.project_a)
        self.assertIsNotNone(result)
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_grep_tool_respects_scope(self):
        """Grep tool should also be subject to scope-aware blocking."""
        _run_hook("Bash", {
            "conversationId": self.session,
            "tool_input": {"command": "rtk graphify query 'overview'"},
            "cwd": str(self.project_a),
        }, cwd=self.project_a)

        result = _run_hook("Grep", {
            "conversationId": self.session,
            "tool_input": {
                "SearchPath": str(self.project_b / "src"),
                "pattern": "print",
                "toolAction": "Exploring codebase",
            },
            "cwd": str(self.project_a),
        }, cwd=self.project_a)
        self.assertIsNotNone(result)
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_twenty_first_graphify_call_is_denied(self):
        """Quota of 20 graphify calls per session should be enforced."""
        # Make 20 calls
        for i in range(20):
            _run_hook("Bash", {
                "conversationId": self.session,
                "tool_input": {"command": f"rtk graphify query 'question {i}'"},
                "cwd": str(self.project_a),
            }, cwd=self.project_a)

        # 21st should be denied
        result = _run_hook("Bash", {
            "conversationId": self.session,
            "tool_input": {"command": "rtk graphify query 'one more'"},
            "cwd": str(self.project_a),
        }, cwd=self.project_a)
        self.assertIsNotNone(result)
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("Maximum 20 Graphify", result["hookSpecificOutput"]["permissionDecisionReason"])

    def test_session_isolation_e2e(self):
        """Different sessions should have fully isolated scopes."""
        session2 = f"e2e-scope-other-{uuid.uuid4()}"
        try:
            # Session 1: graphify in project_a
            _run_hook("Bash", {
                "conversationId": self.session,
                "tool_input": {"command": "rtk graphify query 'overview'"},
                "cwd": str(self.project_a),
            }, cwd=self.project_a)

            # Session 2: graphify in project_b
            _run_hook("Bash", {
                "conversationId": session2,
                "tool_input": {"command": "rtk graphify query 'overview'"},
                "cwd": str(self.project_b),
            }, cwd=self.project_b)

            # Session 1: read project_b should be BLOCKED
            result = _run_hook("Read", {
                "conversationId": self.session,
                "tool_input": {
                    "AbsolutePath": str(self.project_b / "src" / "main.py"),
                    "toolAction": "Exploring codebase",
                },
                "cwd": str(self.project_a),
            }, cwd=self.project_a)
            self.assertIsNotNone(result)
            self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")

            # Session 2: read project_a should be BLOCKED
            result = _run_hook("Read", {
                "conversationId": session2,
                "tool_input": {
                    "AbsolutePath": str(self.project_a / "src" / "main.py"),
                    "toolAction": "Exploring codebase",
                },
                "cwd": str(self.project_b),
            }, cwd=self.project_b)
            self.assertIsNotNone(result)
            self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
        finally:
            _cleanup_session_files(session2)

    def test_yaml_file_bypasses_scope_check(self):
        """YAML files should bypass scope-aware blocking (config/doc files)."""
        _run_hook("Bash", {
            "conversationId": self.session,
            "tool_input": {"command": "rtk graphify query 'overview'"},
            "cwd": str(self.project_a),
        }, cwd=self.project_a)

        yaml_file = self.project_b / "config.yaml"
        yaml_file.write_text("key: value")
        result = _run_hook("Read", {
            "conversationId": self.session,
            "tool_input": {
                "AbsolutePath": str(yaml_file),
                "toolAction": "Exploring codebase",
            },
            "cwd": str(self.project_a),
        }, cwd=self.project_a)
        self.assertIsNone(result)

    def test_toml_file_bypasses_scope_check(self):
        """TOML files should bypass scope-aware blocking."""
        _run_hook("Bash", {
            "conversationId": self.session,
            "tool_input": {"command": "rtk graphify query 'overview'"},
            "cwd": str(self.project_a),
        }, cwd=self.project_a)

        toml_file = self.project_b / "pyproject.toml"
        toml_file.write_text("[tool.pytest]")
        result = _run_hook("Read", {
            "conversationId": self.session,
            "tool_input": {
                "AbsolutePath": str(toml_file),
                "toolAction": "Exploring codebase",
            },
            "cwd": str(self.project_a),
        }, cwd=self.project_a)
        self.assertIsNone(result)


# ===========================================================================
# Tests: Minified Instructions
# ===========================================================================

class TestMinifiedInstructions(unittest.TestCase):
    """Verify the minified instructions retain required keywords and are smaller."""

    def test_instructions_contain_required_keywords(self):
        from installer_graphify import GRAPHIFY_INSTRUCTIONS
        required = [
            "Graphify-only",
            "20 Graphify calls",
            "targeted raw reads",
            "GRAPH_REPORT.md",
            "hard stop",
        ]
        for keyword in required:
            with self.subTest(keyword=keyword):
                self.assertIn(keyword, GRAPHIFY_INSTRUCTIONS)

    def test_instructions_are_minified_vs_original(self):
        """Minified instructions should be at least 30% smaller than original."""
        from installer_graphify import GRAPHIFY_INSTRUCTIONS

        # The original was ~2660 chars / ~700 tokens
        original_char_count = 2660
        new_char_count = len(GRAPHIFY_INSTRUCTIONS)
        savings_pct = (original_char_count - new_char_count) / original_char_count * 100
        self.assertGreater(savings_pct, 30, f"Only {savings_pct:.1f}% savings, expected > 30%")

    def test_instructions_still_mention_graphify_update(self):
        from installer_graphify import GRAPHIFY_INSTRUCTIONS
        self.assertIn("graphify update", GRAPHIFY_INSTRUCTIONS)

    def test_instructions_mention_blocked_tool_recovery(self):
        from installer_graphify import GRAPHIFY_INSTRUCTIONS
        self.assertIn("Blocked Tool Recovery", GRAPHIFY_INSTRUCTIONS)

    def test_guidance_is_concise(self):
        from installer_graphify import GRAPHIFY_GUIDANCE
        # Guidance should be < 300 chars (was ~600+ before)
        self.assertLess(len(GRAPHIFY_GUIDANCE), 300)


# ===========================================================================
# Tests: Instruction file consistency (AGENTS.md, CLAUDE.md, ANTIGRAVITY.md)
# ===========================================================================

class TestInstructionFileConsistency(unittest.TestCase):
    """Verify instruction files have been updated with the minified instructions."""

    def setUp(self):
        self.root = Path(__file__).parent.parent

    def _read_instruction_file(self, name):
        p = self.root / name
        if p.exists():
            return p.read_text()
        return None

    def test_agents_md_contains_minified_instructions(self):
        content = self._read_instruction_file("AGENTS.md")
        if content is None:
            self.skipTest("AGENTS.md not found")
        self.assertIn("Graphify-only", content)
        self.assertIn("20 Graphify calls", content)
        # Should NOT contain the old verbose instructions
        self.assertNotIn("MANDATORY — READ BEFORE ANY CODEBASE EXPLORATION", content)

    def test_claude_md_contains_minified_instructions(self):
        content = self._read_instruction_file("CLAUDE.md")
        if content is None:
            self.skipTest("CLAUDE.md not found")
        self.assertIn("Graphify-only", content)
        self.assertNotIn("MANDATORY — READ BEFORE ANY CODEBASE EXPLORATION", content)

    def test_antigravity_md_contains_minified_instructions(self):
        content = self._read_instruction_file("ANTIGRAVITY.md")
        if content is None:
            self.skipTest("ANTIGRAVITY.md not found")
        self.assertIn("Graphify-only", content)
        self.assertNotIn("MANDATORY — READ BEFORE ANY CODEBASE EXPLORATION", content)

    def test_instruction_files_are_consistent(self):
        """All instruction files should have the same graphify block."""
        files = ["AGENTS.md", "CLAUDE.md", "ANTIGRAVITY.md"]
        blocks = []
        for name in files:
            content = self._read_instruction_file(name)
            if content is None:
                continue
            start = content.find("<!-- ai-coding-config:graphify-start -->")
            end = content.find("<!-- ai-coding-config:graphify-end -->")
            if start != -1 and end != -1:
                blocks.append(content[start:end + len("<!-- ai-coding-config:graphify-end -->")])

        if len(blocks) < 2:
            self.skipTest("Not enough instruction files found")

        for i in range(1, len(blocks)):
            self.assertEqual(blocks[0], blocks[i],
                             f"Graphify blocks differ between instruction files")


# ===========================================================================
# Tests: Bash command scope-aware blocking
# ===========================================================================

class TestBashScopeAwareCaching(unittest.TestCase):
    """Test that Bash commands (cat, grep, etc.) are also subject to scope checking."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.project_a = _make_project(self.tmp, "project-a")
        self.project_b = _make_project(self.tmp, "project-b")
        self.session = f"e2e-bash-scope-{uuid.uuid4()}"

        (self.project_a / "src").mkdir()
        (self.project_a / "src" / "main.py").write_text("print('A')")
        (self.project_b / "src").mkdir()
        (self.project_b / "src" / "main.py").write_text("print('B')")

        # Register project A scope
        _run_hook("Bash", {
            "conversationId": self.session,
            "tool_input": {"command": "rtk graphify query 'overview'"},
            "cwd": str(self.project_a),
        }, cwd=self.project_a)

    def tearDown(self):
        _cleanup_session_files(self.session)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cat_in_allowed_scope_is_allowed(self):
        result = _run_hook("Bash", {
            "conversationId": self.session,
            "tool_input": {
                "command": f"cat {self.project_a / 'src' / 'main.py'}",
                "toolAction": "Exploring codebase",
            },
            "cwd": str(self.project_a),
        }, cwd=self.project_a)
        self.assertIsNone(result)

    def test_cat_outside_scope_is_blocked(self):
        result = _run_hook("Bash", {
            "conversationId": self.session,
            "tool_input": {
                "command": f"cat {self.project_b / 'src' / 'main.py'}",
                "toolAction": "Exploring codebase",
            },
            "cwd": str(self.project_a),
        }, cwd=self.project_a)
        self.assertIsNotNone(result)
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_graphify_update_is_always_allowed(self):
        """graphify update commands should be allowed regardless of scope."""
        result = _run_hook("Bash", {
            "conversationId": self.session,
            "tool_input": {
                "command": "rtk graphify update .",
                "toolAction": "Exploring codebase",
            },
            "cwd": str(self.project_a),
        }, cwd=self.project_a)
        self.assertIsNone(result)

    def test_git_commands_are_allowed(self):
        """Non-read commands like git should not be blocked."""
        result = _run_hook("Bash", {
            "conversationId": self.session,
            "tool_input": {
                "command": "git status",
                "toolAction": "Exploring codebase",
            },
            "cwd": str(self.project_a),
        }, cwd=self.project_a)
        self.assertIsNone(result)

    def test_npm_test_is_allowed(self):
        """Build/test commands should not be blocked."""
        result = _run_hook("Bash", {
            "conversationId": self.session,
            "tool_input": {
                "command": "npm test",
                "toolAction": "Running tests",
            },
            "cwd": str(self.project_a),
        }, cwd=self.project_a)
        self.assertIsNone(result)


# ===========================================================================
# Tests: Token Savings Measurement Script
# ===========================================================================

class TestTokenSavingsScript(unittest.TestCase):
    """Test the measure_token_savings.py script runs without error."""

    def test_measure_script_exits_successfully(self):
        result = subprocess.run(
            [sys.executable, "scripts/measure_token_savings.py"],
            cwd=str(Path(__file__).parent.parent),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, f"Script failed: {result.stderr}")
        self.assertIn("Token Savings", result.stdout)

    def test_measure_script_reports_significant_savings(self):
        result = subprocess.run(
            [sys.executable, "scripts/measure_token_savings.py"],
            cwd=str(Path(__file__).parent.parent),
            capture_output=True,
            text=True,
            check=False,
        )
        # Script exits 1 if savings < 15%
        self.assertEqual(result.returncode, 0)
        self.assertIn("Success", result.stdout)


# ===========================================================================
# Tests: get_graphify_count
# ===========================================================================

class TestGetGraphifyCount(unittest.TestCase):
    """Test the graphify call counter."""

    def setUp(self):
        self.session = f"test-count-{uuid.uuid4()}"

    def tearDown(self):
        _cleanup_session_files(self.session)

    def test_count_starts_at_zero(self):
        count = _hook_mod.get_graphify_count(self.session)
        self.assertEqual(count, 0)

    def test_count_increments_with_graphify_calls(self):
        """Each graphify query should increment the counter."""
        tmp = tempfile.mkdtemp()
        project = _make_project(tmp)
        try:
            for i in range(3):
                _run_hook("Bash", {
                    "conversationId": self.session,
                    "tool_input": {"command": f"rtk graphify query 'q{i}'"},
                    "cwd": str(project),
                }, cwd=project)
            count = _hook_mod.get_graphify_count(self.session)
            self.assertEqual(count, 3)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_count_none_session_returns_zero(self):
        self.assertEqual(_hook_mod.get_graphify_count(None), 0)

    def test_count_empty_session_returns_zero(self):
        self.assertEqual(_hook_mod.get_graphify_count(""), 0)


# ===========================================================================
# Tests: is_inline_python_file_read
# ===========================================================================

class TestIsInlinePythonFileRead(unittest.TestCase):
    """Test detection of inline script-based file reads."""

    def test_python_c_with_open(self):
        self.assertTrue(_hook_mod.is_inline_python_file_read(
            "python3 -c 'print(open(\"README.md\").read())'",
            ["python3"]
        ))

    def test_node_eval_with_readfile(self):
        self.assertTrue(_hook_mod.is_inline_python_file_read(
            "node --eval \"console.log(require('fs').readFileSync('README.md'))\"",
            ["node"]
        ))

    def test_ruby_with_file_read(self):
        self.assertTrue(_hook_mod.is_inline_python_file_read(
            "ruby -e \"puts File.read('README.md')\"",
            ["ruby"]
        ))

    def test_no_inline_flag(self):
        """Commands without -c/-e/--eval should not be detected."""
        self.assertFalse(_hook_mod.is_inline_python_file_read(
            "python3 script.py",
            ["python3"]
        ))

    def test_no_read_keyword(self):
        """Inline command without read-related keywords should not be detected."""
        self.assertFalse(_hook_mod.is_inline_python_file_read(
            "python3 -c 'print(1+1)'",
            ["python3"]
        ))

    def test_non_interpreter(self):
        """Non-interpreter executables should not be detected."""
        self.assertFalse(_hook_mod.is_inline_python_file_read(
            "gcc -c file.c",
            ["gcc"]
        ))


if __name__ == "__main__":
    unittest.main()
