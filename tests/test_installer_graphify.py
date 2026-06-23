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
            "cat config/settings.json",
            "head -n 50 index.html",
            "tail -n 20 log.txt",
            "rtk proxy cat README.md",
            "sed -n '1,10p' README.md",
            "awk '{print}' README.md",
            "jq . package.json",
            "yq . config.yml",
            "hexdump README.md",
            "xxd README.md",
            "strings README.md",
            "ls config",
            "rtk ls src/",
        ):
            with self.subTest(command=command):
                self.assertTrue(install.is_broad_discovery_command(command))

    def test_allows_targeted_reads_and_false_positives(self):
        for command in (
            "rtk graphify query 'architecture overview'",
            "graphify path API Database",
            "graphify explain Router",
            "echo graphify grep rg find fd ack ag",
            "python scripts/graphify_report.py",
        ):
            with self.subTest(command=command):
                self.assertFalse(install.is_broad_discovery_command(command))

    def test_source_read_only_requests_guidance(self):
        result = install.classify_graphify_tool_use(
            "Read", {"file_path": "src/router.py"}, graph_exists=True
        )
        self.assertEqual(result["decision"], "deny")
        self.assertIn("additionalContext", result)
        self.assertIn("BLOCKED", result["additionalContext"])

    def test_directory_listing_requests_guidance(self):
        result = install.classify_graphify_tool_use(
            "Read", {"DirectoryPath": "/repo"}, graph_exists=True
        )
        self.assertEqual(result["decision"], "deny")
        self.assertIn("additionalContext", result)
        self.assertIn("BLOCKED", result["additionalContext"])

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

    def test_graph_json_manual_reads_are_denied(self):
        read_result = install.classify_graphify_tool_use(
            "Read", {"file_path": "graphify-out/graph.json"}, graph_exists=True
        )
        self.assertEqual(read_result["decision"], "deny")
        self.assertIn("graphify CLI", read_result["additionalContext"])

        bash_result = install.classify_graphify_tool_use(
            "Bash", {"command": "cat graphify-out/graph.json"}, graph_exists=True
        )
        self.assertEqual(bash_result["decision"], "deny")
        self.assertIn("graphify CLI", bash_result["additionalContext"])

    def test_normal_test_ls_and_which_commands_are_allowed(self):
        for command in ("test -f package.json", "which node", "which graphify", "command -v graphify"):
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
                "Read", {"file_path": "docs/specs_next_index.md"}, graph_exists=True
            ),
            {"decision": "allow"},
        )
        self.assertEqual(
            install.classify_graphify_tool_use(
                "Bash", {"command": "rg Router src"}, graph_exists=False
            ),
            {"decision": "allow"},
        )

    def test_denies_inline_python_read_via_classifier(self):
        for command in (
            "python3 -c 'print(open(\"README.md\").read())'",
            "python -c \"import pathlib; print(pathlib.Path('README.md').read_text())\"",
            "node -e \"require('fs').readFileSync('README.md')\"",
            "node --eval \"console.log(require('fs').readFileSync('README.md'))\"",
            "perl -ne 'print' README.md",
            "perl -pe 'print' README.md",
            "ruby -e \"puts File.read('README.md')\"",
            "php -r \"echo file_get_contents('README.md');\"",
            "python3 -c \"import os; print(os.listdir('.'))\"",
            "python -c \"import os; next(os.walk('.'))\"",
            "python3 -c \"import glob; print(glob.glob('*.py'))\"",
            "node -e \"console.log(require('fs').readdirSync('.'))\"",
        ):
            with self.subTest(command=command):
                result = install.classify_graphify_tool_use(
                    "Bash", {"command": command}, graph_exists=True
                )
                self.assertEqual(result["decision"], "deny")
                self.assertIn("Inline script execution for exploration is blocked", result["additionalContext"])


class TestGraphifySettingsMerge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        (self.project / "graphify-out").mkdir()
        (self.project / "graphify-out" / "graph.json").write_text("{}")
        self.home_patcher = mock.patch.object(Path, "home", return_value=self.project)
        self.home_patcher.start()

    def tearDown(self):
        self.home_patcher.stop()
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
            5,
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
        self.assertIn("Graphify-only", second)
        self.assertIn("20 Graphify calls", second)
        self.assertIn("hard stop", second)

    def test_claude_hook_denies_twenty_first_graphify_call_in_same_session(self):
        # Get the hook script directly — avoids shell quoting issues on Windows
        # where subprocess.run(shell=True) uses cmd.exe, not bash.
        from installer_graphify import _hook_classifier_script
        script = _hook_classifier_script("Bash", True)
        payload = {
            "session_id": f"quota-test-{uuid.uuid4()}",
            "tool_input": {"command": "rtk graphify query 'architecture'"},
        }
        run_kwargs = dict(
            args=[sys.executable, "-c", script],
            cwd=self.project,
        )

        outputs = []
        for _ in range(21):
            result = subprocess.run(
                **run_kwargs,
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                check=False,
            )
            outputs.append(result.stdout.strip())

        self.assertEqual(outputs[:20], [""] * 20)
        self.assertEqual(
            json.loads(outputs[20])["hookSpecificOutput"]["permissionDecision"],
            "deny",
        )

    def test_claude_hook_denies_twenty_first_graphify_call_with_conversation_id(self):
        from installer_graphify import _hook_classifier_script
        script = _hook_classifier_script("Bash", True)
        payload = {
            "conversationId": f"quota-test-{uuid.uuid4()}",
            "tool_input": {"command": "rtk graphify query 'architecture'"},
        }
        run_kwargs = dict(
            args=[sys.executable, "-c", script],
            cwd=self.project,
        )

        outputs = []
        for _ in range(21):
            result = subprocess.run(
                **run_kwargs,
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                check=False,
            )
            outputs.append(result.stdout.strip())

        self.assertEqual(outputs[:20], [""] * 20)
        self.assertEqual(
            json.loads(outputs[20])["hookSpecificOutput"]["permissionDecision"],
            "deny",
        )

    def test_claude_hook_denies_rtk_proxy_bypass(self):
        from installer_graphify import _hook_classifier_script
        script = _hook_classifier_script("Bash", True)
        payload = {
            "tool_input": {"command": "rtk proxy cat README.md"},
        }
        result = subprocess.run(
            args=[sys.executable, "-c", script],
            cwd=self.project,
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
        )
        data = json.loads(result.stdout.strip())
        self.assertEqual(data["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("Direct search/read tools are not available", data["hookSpecificOutput"]["permissionDecisionReason"])

    def test_claude_hook_denies_inline_python_read_bypass(self):
        from installer_graphify import _hook_classifier_script
        script = _hook_classifier_script("Bash", True)
        payload = {
            "tool_input": {"command": "python3 -c 'print(open(\"README.md\").read())'"},
        }
        result = subprocess.run(
            args=[sys.executable, "-c", script],
            cwd=self.project,
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
        )
        data = json.loads(result.stdout.strip())
        self.assertEqual(data["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("Inline script execution for exploration is blocked", data["hookSpecificOutput"]["permissionDecisionReason"])

    def test_claude_hook_balanced_strict_targeted_reads(self):
        from installer_graphify import _hook_classifier_script
        script_bash = _hook_classifier_script("Bash", True)
        script_read = _hook_classifier_script("Read", True)

        session_id = f"balanced-strict-test-{uuid.uuid4()}"

        # 1. Initially (g_count = 0), a read of a source file (e.g. main.py) in exploration is denied
        payload_read_0 = {
            "conversationId": session_id,
            "tool_input": {"AbsolutePath": "src/main.py", "toolAction": "Exploring codebase"},
        }
        res_read_0 = subprocess.run(
            args=[sys.executable, "-c", script_read],
            cwd=self.project,
            input=json.dumps(payload_read_0),
            capture_output=True,
            text=True,
            check=False,
        )
        data_read_0 = json.loads(res_read_0.stdout.strip())
        self.assertEqual(data_read_0["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("Direct search/read tools are not available", data_read_0["hookSpecificOutput"]["permissionDecisionReason"])

        # 2. Initially (g_count = 0), a sed command in Bash is denied
        payload_bash_0 = {
            "conversationId": session_id,
            "tool_input": {"command": "rtk sed -n '1,10p' src/main.py", "toolAction": "Exploring"},
        }
        res_bash_0 = subprocess.run(
            args=[sys.executable, "-c", script_bash],
            cwd=self.project,
            input=json.dumps(payload_bash_0),
            capture_output=True,
            text=True,
            check=False,
        )
        data_bash_0 = json.loads(res_bash_0.stdout.strip())
        self.assertEqual(data_bash_0["hookSpecificOutput"]["permissionDecision"], "deny")

        # 3. We run a Graphify call to increment the counter
        payload_graphify = {
            "conversationId": session_id,
            "tool_input": {"command": "rtk graphify query 'what does main do'"},
        }
        subprocess.run(
            args=[sys.executable, "-c", script_bash],
            cwd=self.project,
            input=json.dumps(payload_graphify),
            capture_output=True,
            text=True,
            check=False,
        )

        # 4. Now (g_count = 1), the read tool is allowed for main.py (even in exploration)
        res_read_1 = subprocess.run(
            args=[sys.executable, "-c", script_read],
            cwd=self.project,
            input=json.dumps(payload_read_0),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res_read_1.stdout.strip(), "")

        # 5. Now (g_count = 1), the sed command in Bash is allowed
        res_bash_1 = subprocess.run(
            args=[sys.executable, "-c", script_bash],
            cwd=self.project,
            input=json.dumps(payload_bash_0),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res_bash_1.stdout.strip(), "")

        # 6. Search command (like grep) in Bash is STILL denied
        payload_grep = {
            "conversationId": session_id,
            "tool_input": {"command": "rtk grep 'main' src/", "toolAction": "Exploring"},
        }
        res_grep = subprocess.run(
            args=[sys.executable, "-c", script_bash],
            cwd=self.project,
            input=json.dumps(payload_grep),
            capture_output=True,
            text=True,
            check=False,
        )
        data_grep = json.loads(res_grep.stdout.strip())
        self.assertEqual(data_grep["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("Direct search/read tools are not available", data_grep["hookSpecificOutput"]["permissionDecisionReason"])

    def test_gemini_merge_preserves_settings_and_is_idempotent(self):
        settings_path = self.project / ".gemini" / "settings.json"
        settings_path.parent.mkdir()
        settings_path.write_text(json.dumps({
            "theme": "dark",
            "hooks": {"PreToolUse": [
                {"matcher": "write_file", "hooks": [{"type": "command", "command": "custom"}]}
            ]},
        }))

        install.configure_gemini_project(self.project)
        first = settings_path.read_text()
        install.configure_gemini_project(self.project)
        data = json.loads(settings_path.read_text())

        self.assertEqual(first, settings_path.read_text())
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(len(data["hooks"]["PreToolUse"]), 5)
        self.assertEqual(
            sum(install.is_managed_graphify_hook(h) for h in data["hooks"]["PreToolUse"]),
            4,
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
        self.assertEqual(len(data["hooks"]["PreToolUse"]), 6)

    def test_one_cli_failure_does_not_stop_other_clis(self):
        with mock.patch.object(
            install, "configure_claude_project", side_effect=PermissionError("read-only")
        ):
            results = install.configure_project_assistants(
                self.project, ["claude", "gemini", "codex", "copilot"]
            )

        self.assertFalse(results["claude"])
        self.assertTrue(results["gemini"])
        self.assertTrue(results["codex"])
        self.assertTrue(results["copilot"])
        self.assertTrue((self.project / ".gemini" / "settings.json").exists())
        self.assertTrue((self.project / ".codex" / "hooks.json").exists())
        self.assertTrue((self.project / ".vscode" / "settings.json").exists())

    def test_copilot_config_creates_settings_and_merges_instructions(self):
        # Setup mock templates in mock repo directory
        copilot_dir = self.project / "copilot"
        copilot_dir.mkdir()
        (copilot_dir / "settings.json").write_text(json.dumps({
            "github.copilot.chat.codeGeneration.instructions": [{"filePath": ".github/copilot-instructions.md"}],
            "search.exclude": {"**/node_modules": True, "**/graphify-out": True},
            "files.watcherExclude": {"**/node_modules/**": True, "**/graphify-out/**": True}
        }))
        (copilot_dir / "copilot-instructions.md").write_text("# Mock Copilot Instructions\n")

        # Mock __file__ to point inside our mock repo
        with mock.patch("installer_graphify.__file__", str(self.project / "installer_graphify.py")):
            install.configure_copilot_project(self.project)

        settings_path = self.project / ".vscode" / "settings.json"
        self.assertTrue(settings_path.exists())
        settings = json.loads(settings_path.read_text())
        self.assertEqual(settings["github.copilot.chat.codeGeneration.instructions"][0]["filePath"], ".github/copilot-instructions.md")

        instructions_path = self.project / ".github" / "copilot-instructions.md"
        self.assertTrue(instructions_path.exists())
        self.assertIn("# Mock Copilot Instructions", instructions_path.read_text())
        self.assertIn("ai-coding-config:graphify-start", instructions_path.read_text())

    def test_claude_hook_denies_path_leak_in_write(self):
        from installer_graphify import _hook_classifier_script
        script = _hook_classifier_script("Write", True)
        leak_path = (self.project / "projects" / "main.py").as_posix()
        payload = {
            "tool_input": {
                "file_path": "src/leak.py",
                "code_content": f"import os\n# Path leak: {leak_path}\nprint('hello')"
            }
        }
        import os
        env = os.environ.copy()
        env["HOME"] = str(self.project)
        env["USERPROFILE"] = str(self.project)
        result = subprocess.run(
            args=[sys.executable, "-c", script],
            cwd=self.project,
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        data = json.loads(result.stdout.strip())
        self.assertEqual(data["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("Absolute home directory path detected", data["hookSpecificOutput"]["permissionDecisionReason"])

    def test_claude_hook_denies_path_leak_in_edit(self):
        from installer_graphify import _hook_classifier_script
        script = _hook_classifier_script("Edit", True)
        leak_path = (self.project / "projects" / "leak").as_posix()
        payload = {
            "tool_input": {
                "file_path": "src/leak.py",
                "ReplacementChunks": [
                    {
                        "StartLine": 1,
                        "EndLine": 5,
                        "TargetContent": "print('hello')",
                        "ReplacementContent": f"print('{leak_path}')"
                    }
                ]
            }
        }
        import os
        env = os.environ.copy()
        env["HOME"] = str(self.project)
        env["USERPROFILE"] = str(self.project)
        result = subprocess.run(
            args=[sys.executable, "-c", script],
            cwd=self.project,
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        data = json.loads(result.stdout.strip())
        self.assertEqual(data["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("Absolute home directory path detected", data["hookSpecificOutput"]["permissionDecisionReason"])

    def test_claude_hook_allows_no_path_leak_in_write(self):
        from installer_graphify import _hook_classifier_script
        script = _hook_classifier_script("Write", True)
        payload = {
            "tool_input": {
                "file_path": "src/leak.py",
                "code_content": "import os\n# Safe tilde path: ~/projects/main.py\nprint('hello')"
            }
        }
        import os
        env = os.environ.copy()
        env["HOME"] = str(self.project)
        env["USERPROFILE"] = str(self.project)
        result = subprocess.run(
            args=[sys.executable, "-c", script],
            cwd=self.project,
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.stdout.strip(), "")



class TestGraphifyInstructions(unittest.TestCase):
    def test_balanced_strict_instructions(self):
        instructions = install.GRAPHIFY_INSTRUCTIONS
        self.assertIn("Graphify-only", instructions)
        self.assertIn("20 Graphify calls", instructions)
        self.assertIn("targeted raw reads", instructions)
        self.assertIn("GRAPH_REPORT.md", instructions)


if __name__ == "__main__":
    unittest.main()
