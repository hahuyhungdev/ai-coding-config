import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parent.parent
HOOK_PATH = REPO_DIR / "claude" / "hooks" / "graphify_pre_tool.py"


def _run_hook(tool: str, payload: dict, cwd: Path) -> dict:
    result = subprocess.run(
        [
            sys.executable,
            str(HOOK_PATH),
            "--tool",
            tool,
            "--client",
            "claude",
        ],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(cwd),
        check=True,
    )
    if not result.stdout:
        return {}
    return json.loads(result.stdout)


def _decision(output: dict) -> str | None:
    return output.get("hookSpecificOutput", {}).get("permissionDecision")


def _context(output: dict) -> str:
    return output.get("hookSpecificOutput", {}).get("additionalContext", "")


class TestGraphifyRuntimeHookPolicy(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.project = self.tmp / "project"
        self.project.mkdir()
        (self.project / "graphify-out").mkdir()
        (self.project / "graphify-out" / "graph.json").write_text("{}")
        (self.project / "docs").mkdir()
        (self.project / "docs" / "spec.md").write_text("# Spec")
        (self.project / "app").mkdir()
        (self.project / "app" / "main.py").write_text("print('hello')\n")
        self.external_cwd = self.tmp / "outside"
        self.external_cwd.mkdir()
        self.session = "test-runtime-hook-policy"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        for path in Path(tempfile.gettempdir()).glob(f"ai-coding-config-*{self.session}*"):
            path.unlink(missing_ok=True)

    def test_capitalized_cwd_enables_graph_detection_for_directory_reads(self):
        output = _run_hook(
            "Read",
            {
                "conversationId": self.session,
                "tool_input": {
                    "path": str(self.project / "app"),
                    "toolAction": "Exploring codebase",
                },
                "Cwd": str(self.project),
            },
            cwd=self.external_cwd,
        )

        self.assertEqual(_decision(output), "deny")
        self.assertIn("Graphify", _context(output))

    def test_gemini_directory_path_reads_before_graphify_are_denied(self):
        output = _run_hook(
            "Read",
            {
                "conversationId": self.session,
                "tool_input": {
                    "DirectoryPath": str(self.project),
                    "toolAction": "Exploring codebase",
                },
                "Cwd": str(self.project),
            },
            cwd=self.external_cwd,
        )

        self.assertEqual(_decision(output), "deny")
        self.assertIn("Graphify", _context(output))

    def test_docs_file_reads_before_graphify_are_allowed(self):
        output = _run_hook(
            "Read",
            {
                "conversationId": self.session,
                "tool_input": {
                    "file_path": str(self.project / "docs" / "spec.md"),
                    "toolAction": "Exploring codebase",
                },
                "Cwd": str(self.project),
            },
            cwd=self.external_cwd,
        )

        self.assertIsNone(_decision(output))

    def test_exact_source_file_reads_before_graphify_are_allowed(self):
        output = _run_hook(
            "Read",
            {
                "conversationId": self.session,
                "tool_input": {
                    "file_path": str(self.project / "app" / "main.py"),
                    "toolAction": "Exploring codebase",
                },
                "Cwd": str(self.project),
            },
            cwd=self.external_cwd,
        )

        self.assertIsNone(_decision(output))

    def test_bash_exact_file_read_before_graphify_is_allowed(self):
        output = _run_hook(
            "Bash",
            {
                "conversationId": self.session,
                "tool_input": {
                    "command": f"cat {self.project / 'app' / 'main.py'}",
                    "toolAction": "Exploring codebase",
                },
                "Cwd": str(self.project),
            },
            cwd=self.external_cwd,
        )

        self.assertIsNone(_decision(output))

    def test_graphify_skill_read_before_graphify_is_denied(self):
        output = _run_hook(
            "Read",
            {
                "conversationId": self.session,
                "tool_input": {
                    "file_path": "/home/mockuser/.gemini/config/skills/graphify/SKILL.md",
                    "toolAction": "Exploring codebase",
                },
                "Cwd": str(self.project),
            },
            cwd=self.external_cwd,
        )

        self.assertEqual(_decision(output), "deny")
        self.assertIn("Graphify skill docs", _context(output))
        self.assertIn("rtk graphify query", _context(output))

    def test_bash_graphify_skill_read_before_graphify_is_denied(self):
        output = _run_hook(
            "Bash",
            {
                "conversationId": self.session,
                "tool_input": {
                    "command": "cat /home/mockuser/.gemini/config/skills/graphify/SKILL.md",
                    "toolAction": "Exploring codebase",
                },
                "Cwd": str(self.project),
            },
            cwd=self.external_cwd,
        )

        self.assertEqual(_decision(output), "deny")
        self.assertIn("Graphify skill docs", _context(output))
        self.assertIn("rtk graphify query", _context(output))

    def test_bash_directory_listing_before_graphify_is_denied(self):
        output = _run_hook(
            "Bash",
            {
                "conversationId": self.session,
                "tool_input": {
                    "command": f"ls {self.project / 'app'}",
                    "toolAction": "Exploring codebase",
                },
                "Cwd": str(self.project),
            },
            cwd=self.external_cwd,
        )

        self.assertEqual(_decision(output), "deny")
        self.assertIn("Graphify", _context(output))
        self.assertIn("rtk graphify query", _context(output))
        self.assertIn("--budget 1200", _context(output))

    def test_graph_report_manual_read_is_denied(self):
        (self.project / "graphify-out" / "GRAPH_REPORT.md").write_text("# Full report\n")

        output = _run_hook(
            "Read",
            {
                "conversationId": self.session,
                "tool_input": {
                    "file_path": str(self.project / "graphify-out" / "GRAPH_REPORT.md"),
                    "toolAction": "Exploring codebase",
                },
                "Cwd": str(self.project),
            },
            cwd=self.external_cwd,
        )

        self.assertEqual(_decision(output), "deny")
        self.assertIn("GRAPH_REPORT.md", _context(output))

    def test_hook_does_not_write_debug_snapshot_by_default(self):
        debug_path = REPO_DIR / "hook-debug-claude.json"
        debug_path.unlink(missing_ok=True)

        _run_hook(
            "Bash",
            {
                "conversationId": self.session,
                "tool_input": {"command": "rtk graphify query 'overview'"},
                "Cwd": str(self.project),
            },
            cwd=self.external_cwd,
        )

        self.assertFalse(debug_path.exists())

    def test_docs_reads_after_graphify_are_allowed(self):
        _run_hook(
            "Bash",
            {
                "conversationId": self.session,
                "tool_input": {"command": "rtk graphify query 'first page spec'"},
                "Cwd": str(self.project),
            },
            cwd=self.external_cwd,
        )

        output = _run_hook(
            "Read",
            {
                "conversationId": self.session,
                "tool_input": {
                    "file_path": str(self.project / "docs" / "spec.md"),
                    "toolAction": "Exploring codebase",
                },
                "Cwd": str(self.project),
            },
            cwd=self.external_cwd,
        )

        self.assertIsNone(_decision(output))

    def test_graph_json_manual_read_is_denied(self):
        output = _run_hook(
            "Read",
            {
                "conversationId": self.session,
                "tool_input": {
                    "file_path": str(self.project / "graphify-out" / "graph.json"),
                    "toolAction": "Exploring codebase",
                },
                "Cwd": str(self.project),
            },
            cwd=self.external_cwd,
        )

        self.assertEqual(_decision(output), "deny")
        self.assertIn("graphify CLI", _context(output))

    def test_scratch_reader_script_creation_is_denied(self):
        output = _run_hook(
            "Write",
            {
                "conversationId": self.session,
                "tool_input": {
                    "file_path": str(self.project / "scratch_read.py"),
                    "code_content": (
                        "from pathlib import Path\n"
                        "print(Path('docs/spec.md').read_text())\n"
                    ),
                    "toolAction": "Exploring codebase",
                },
                "Cwd": str(self.project),
            },
            cwd=self.external_cwd,
        )

        self.assertEqual(_decision(output), "deny")
        self.assertIn("scratch reader scripts", _context(output))
        self.assertIn("rtk graphify query", _context(output))

    def test_scratch_reader_script_execution_is_denied(self):
        (self.project / "scratch_read.py").write_text(
            "from pathlib import Path\nprint(Path('docs/spec.md').read_text())\n"
        )

        output = _run_hook(
            "Bash",
            {
                "conversationId": self.session,
                "tool_input": {
                    "command": "python3 scratch_read.py",
                    "toolAction": "Exploring codebase",
                },
                "Cwd": str(self.project),
            },
            cwd=self.external_cwd,
        )

        self.assertEqual(_decision(output), "deny")
        self.assertIn("scratch reader scripts", _context(output))
        self.assertIn("targeted reads", _context(output))
