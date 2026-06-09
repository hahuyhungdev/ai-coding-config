import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parent.parent


class TestInstallerCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.project = self.root / "project"
        self.bin = self.root / "bin"
        self.home.mkdir()
        self.project.mkdir()
        self.bin.mkdir()
        self._write_executable(
            "graphify",
            """#!/bin/sh
if [ "$1" = "update" ]; then
  mkdir -p graphify-out
  printf '{}' > graphify-out/graph.json
fi
exit 0
""",
        )
        for executable in ("claude", "codex", "agy", "node"):
            self._write_executable(executable, "#!/bin/sh\nexit 0\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _write_executable(self, name, content):
        path = self.bin / name
        path.write_text(content)
        path.chmod(0o755)

    def _run(self, *args, include_graphify=True):
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env["PATH"] = str(self.bin)
        if not include_graphify and (self.bin / "graphify").exists():
            (self.bin / "graphify").rename(self.bin / "graphify.disabled")
        return subprocess.run(
            [sys.executable, str(REPO_DIR / "install.py"), *args, "--project", str(self.project)],
            cwd=self.project,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_all_force_is_idempotent(self):
        first = self._run("--all", "--force")
        self.assertEqual(first.returncode, 0, first.stderr)
        paths = [
            self.project / ".claude" / "settings.json",
            self.project / ".gemini" / "settings.json",
            self.project / ".codex" / "hooks.json",
        ]
        before = {path: path.read_text() for path in paths}

        second = self._run("--all", "--force")

        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(before, {path: path.read_text() for path in paths})
        for path in paths:
            json.loads(path.read_text())

    def test_individual_cli_flags_only_configure_selected_project(self):
        cases = {
            "--claude": self.project / ".claude" / "settings.json",
            "--codex": self.project / ".codex" / "hooks.json",
            "--agy": self.project / ".gemini" / "settings.json",
        }
        for flag, expected in cases.items():
            with self.subTest(flag=flag):
                for name in (".claude", ".codex", ".gemini"):
                    target = self.project / name
                    if target.exists():
                        import shutil
                        shutil.rmtree(target)
                result = self._run(flag, "--force")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(expected.exists())
                created = [name for name in (".claude", ".codex", ".gemini") if (self.project / name).exists()]
                self.assertEqual(created, [expected.parent.name])

    def test_none_does_not_configure_project_assistants(self):
        result = self._run("--none", "--force")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.project / ".claude").exists())
        self.assertFalse((self.project / ".gemini").exists())
        self.assertFalse((self.project / ".codex").exists())

    def test_missing_graphify_falls_back_without_project_hooks(self):
        (self.bin / "graphify").unlink()
        result = self._run("--all", "--force", include_graphify=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.project / "graphify-out").exists())
        self.assertFalse((self.project / ".claude").exists())

    def test_installs_global_cli_wrapper(self):
        result = self._run("--all", "--force")
        self.assertEqual(result.returncode, 0, result.stderr)
        wrapper_path = self.home / ".local" / "bin" / "ai-config"
        self.assertTrue(wrapper_path.is_file())
        self.assertIn("install.py", wrapper_path.read_text())
        self.assertIn("init", wrapper_path.read_text())
        # Check permissions (executable)
        self.assertTrue(os.access(wrapper_path, os.X_OK))


if __name__ == "__main__":
    unittest.main()
