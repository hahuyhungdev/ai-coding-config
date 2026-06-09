import json
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

import install


class TestGraphifyCommandClassification(unittest.TestCase):
    def test_blocks_broad_discovery_executables(self):
        for command in (
            "grep -R needle src",
            "rtk rg needle .",
            "find src -name '*.py'",
            "fd service src",
            "ack controller",
            "ag repository",
            "graphify query 'architecture' | grep service",
        ):
            with self.subTest(command=command):
                self.assertTrue(install.is_broad_discovery_command(command))

    def test_allows_targeted_reads_and_false_positives(self):
        for command in (
            "rtk graphify query 'architecture overview'",
            "graphify path API Database",
            "graphify explain Router",
            "sed -n '1,120p' src/router.py",
            "cat config/settings.json",
            "echo graphify grep rg find fd ack ag",
            "python scripts/graphify_report.py",
        ):
            with self.subTest(command=command):
                self.assertFalse(install.is_broad_discovery_command(command))

    def test_source_read_only_requests_guidance(self):
        result = install.classify_graphify_tool_use(
            "Read", {"file_path": "src/router.py"}, graph_exists=True
        )
        self.assertEqual(result["decision"], "allow")
        self.assertIn("additionalContext", result)
        self.assertNotIn("BLOCKED", result["additionalContext"])

    def test_builtin_grep_is_denied_when_graph_exists(self):
        result = install.classify_graphify_tool_use(
            "Grep", {"pattern": "Router", "path": "src"}, graph_exists=True
        )
        self.assertEqual(result["decision"], "deny")
        self.assertIn("BLOCKED", result["additionalContext"])

    def test_graphify_availability_probes_are_allowed(self):
        for command in (
            "test -f graphify-out/graph.json",
            "ls /repo/graphify-out/graph.json",
        ):
            with self.subTest(command=command):
                result = install.classify_graphify_tool_use(
                    "Bash", {"command": command}, graph_exists=True
                )
                self.assertEqual(result["decision"], "allow")

    def test_normal_test_ls_and_which_commands_are_allowed(self):
        for command in ("test -f package.json", "ls config", "which node", "which graphify", "command -v graphify"):
            with self.subTest(command=command):
                result = install.classify_graphify_tool_use(
                    "Bash", {"command": command}, graph_exists=True
                )
                self.assertEqual(result, {"decision": "allow"})

    def test_config_read_and_missing_graph_are_ignored(self):
        self.assertEqual(
            install.classify_graphify_tool_use(
                "Read", {"file_path": ".claude/settings.json"}, graph_exists=True
            ),
            {"decision": "allow"},
        )
        self.assertEqual(
            install.classify_graphify_tool_use(
                "Bash", {"command": "rg Router src"}, graph_exists=False
            ),
            {"decision": "allow"},
        )


class TestGraphifySettingsMerge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        (self.project / "graphify-out").mkdir()
        (self.project / "graphify-out" / "graph.json").write_text("{}")

    def tearDown(self):
        self.tmp.cleanup()

    def test_preserves_existing_hooks_and_replaces_managed_hooks(self):
        settings_path = self.project / ".claude" / "settings.json"
        settings_path.parent.mkdir()
        settings_path.write_text(json.dumps({
            "permissions": {"allow": ["Bash(npm test)"]},
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Write", "hooks": [{"type": "command", "command": "custom-hook"}]},
                    {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo 'BLOCKED by graphify hook: Use graphify query'"}]},
                    {"matcher": "Read|Glob", "hooks": [{"type": "command", "command": "echo 'graphify: knowledge graph at graphify-out/'"}]},
                    install.managed_claude_hooks()[0],
                    install.managed_claude_hooks()[0],
                ],
                "PostToolUse": [{"matcher": "Edit", "hooks": [{"type": "command", "command": "format"}]}],
            },
        }))

        install.configure_claude_project(self.project)
        first = settings_path.read_text()
        install.configure_claude_project(self.project)
        second = settings_path.read_text()
        data = json.loads(second)

        self.assertEqual(first, second)
        self.assertEqual(data["permissions"]["allow"], ["Bash(npm test)"])
        self.assertEqual(data["hooks"]["PostToolUse"][0]["matcher"], "Edit")
        self.assertEqual(
            sum(install.is_managed_graphify_hook(h) for h in data["hooks"]["PreToolUse"]),
            3,
        )
        self.assertTrue(any(h.get("matcher") == "Write" for h in data["hooks"]["PreToolUse"]))
        commands = json.dumps(data["hooks"]["PreToolUse"])
        self.assertNotIn("BLOCKED by graphify hook: Use graphify query", commands)
        self.assertNotIn("graphify: knowledge graph at graphify-out/", commands)

    def test_project_instructions_are_merged_and_idempotent(self):
        instruction_path = self.project / "CLAUDE.md"
        instruction_path.write_text("# Existing project rules\n\nKeep this text.\n")

        install.configure_claude_project(self.project)
        first = instruction_path.read_text()
        install.configure_claude_project(self.project)
        second = instruction_path.read_text()

        self.assertEqual(first, second)
        self.assertIn("Keep this text.", second)
        self.assertEqual(second.count("ai-coding-config:graphify-start"), 1)
        self.assertIn("FIRST tool call", second)
        self.assertIn("3 Graphify calls total", second)
        self.assertIn("hard stop", second)

    def test_claude_hook_denies_fourth_graphify_call_in_same_session(self):
        import base64
        command = install.managed_claude_hooks()[0]["hooks"][0]["command"]
        payload = {
            "session_id": f"quota-test-{uuid.uuid4()}",
            "tool_input": {"command": "rtk graphify query 'architecture'"},
        }

        # On Windows, cmd.exe can't parse shlex.quote single quotes.
        # Extract the base64-encoded script and run directly.
        if sys.platform == "win32" and "base64" in command:
            m_start = command.find("b64decode('") + len("b64decode('")
            m_end = command.find("')", m_start)
            script = base64.b64decode(command[m_start:m_end]).decode("utf-8")
            run_kwargs = dict(
                args=[sys.executable, "-c", script],
                cwd=self.project,
            )
        else:
            run_kwargs = dict(
                args=command,
                shell=True,
                cwd=self.project,
            )

        outputs = []
        for _ in range(4):
            result = subprocess.run(
                **run_kwargs,
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                check=False,
            )
            outputs.append(result.stdout.strip())

        self.assertEqual(outputs[:3], ["", "", ""])
        self.assertEqual(
            json.loads(outputs[3])["hookSpecificOutput"]["permissionDecision"],
            "deny",
        )

    def test_gemini_merge_preserves_settings_and_is_idempotent(self):
        settings_path = self.project / ".gemini" / "settings.json"
        settings_path.parent.mkdir()
        settings_path.write_text(json.dumps({
            "theme": "dark",
            "hooks": {"BeforeTool": [
                {"matcher": "write_file", "hooks": [{"type": "command", "command": "custom"}]}
            ]},
        }))

        install.configure_gemini_project(self.project)
        first = settings_path.read_text()
        install.configure_gemini_project(self.project)
        data = json.loads(settings_path.read_text())

        self.assertEqual(first, settings_path.read_text())
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(len(data["hooks"]["BeforeTool"]), 3)
        self.assertEqual(
            sum(install.is_managed_graphify_hook(h) for h in data["hooks"]["BeforeTool"]),
            2,
        )

    def test_invalid_json_is_backed_up(self):
        settings_path = self.project / ".claude" / "settings.json"
        settings_path.parent.mkdir()
        settings_path.write_text("{broken")

        install.configure_claude_project(self.project)

        self.assertEqual(len(list(settings_path.parent.glob("settings.json.backup-*"))), 1)
        json.loads(settings_path.read_text())

    def test_codex_empty_file_collision_becomes_directory(self):
        codex_path = self.project / ".codex"
        codex_path.write_text("")

        install.configure_codex_project(self.project)

        self.assertTrue(codex_path.is_dir())
        self.assertTrue((codex_path / "hooks.json").is_file())
        self.assertEqual(len(list(self.project.glob(".codex.backup-*"))), 1)

    def test_codex_non_empty_file_collision_is_preserved_in_backup(self):
        codex_path = self.project / ".codex"
        codex_path.write_text("important local data")

        install.configure_codex_project(self.project)

        backups = list(self.project.glob(".codex.backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), "important local data")
        self.assertTrue((codex_path / "hooks.json").exists())

    def test_codex_directory_merges_existing_hooks(self):
        hooks_path = self.project / ".codex" / "hooks.json"
        hooks_path.parent.mkdir()
        hooks_path.write_text(json.dumps({
            "custom": True,
            "hooks": {"PreToolUse": [
                {"matcher": "Write", "hooks": [{"type": "command", "command": "custom"}]}
            ]},
        }))

        install.configure_codex_project(self.project)
        data = json.loads(hooks_path.read_text())

        self.assertTrue(data["custom"])
        self.assertEqual(len(data["hooks"]["PreToolUse"]), 2)

    def test_one_cli_failure_does_not_stop_other_clis(self):
        with mock.patch.object(
            install, "configure_claude_project", side_effect=PermissionError("read-only")
        ):
            results = install.configure_project_assistants(
                self.project, ["claude", "gemini", "codex"]
            )

        self.assertFalse(results["claude"])
        self.assertTrue(results["gemini"])
        self.assertTrue(results["codex"])
        self.assertTrue((self.project / ".gemini" / "settings.json").exists())
        self.assertTrue((self.project / ".codex" / "hooks.json").exists())


class TestGraphifyInstructions(unittest.TestCase):
    def test_balanced_strict_instructions(self):
        instructions = install.GRAPHIFY_INSTRUCTIONS
        self.assertIn("broad `rtk graphify query", instructions)
        self.assertIn("at most 2 follow-up", instructions)
        self.assertIn("targeted raw reads", instructions)
        self.assertIn("GRAPH_REPORT.md", instructions)


if __name__ == "__main__":
    unittest.main()
