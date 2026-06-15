import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parent.parent
SCRIPT = REPO_DIR / "tools" / "codex-account" / "codex-account.py"
WRAPPER = REPO_DIR / "tools" / "codex" / "codex"


class TestCodexAccount(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.codex_home = self.home / ".codex"
        self.codex_home.mkdir()
        self.sessions = self.codex_home / "sessions" / "2026" / "06" / "15"
        self.sessions.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *args, stdin=None):
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env["CODEX_HOME"] = str(self.codex_home)
        env["PYTHONPYCACHEPREFIX"] = str(self.home / "pycache")
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            env=env,
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
        )

    def _run_wrapper(self, *args):
        real_codex = self.home / "codex-bin"
        real_codex.write_text("#!/bin/sh\nprintf 'REAL_CODEX:%s\\n' \"$*\"\n", encoding="utf-8")
        real_codex.chmod(0o755)
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env["CODEX_HOME"] = str(self.codex_home)
        env["CODEX_REAL_BIN"] = str(real_codex)
        env["PYTHONPYCACHEPREFIX"] = str(self.home / "pycache")
        return subprocess.run(
            [str(WRAPPER), *args],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def _auth(self, account_id, refresh_token="refresh"):
        return {
            "auth_mode": "chatgpt",
            "OPENAI_API_KEY": None,
            "tokens": {
                "access_token": "not-a-jwt",
                "refresh_token": refresh_token,
                "account_id": account_id,
            },
            "last_refresh": "2026-06-15T00:00:00Z",
        }

    def test_add_list_and_use_accounts_without_printing_tokens(self):
        first = self._auth("acct-one", refresh_token="refresh-one")
        second = self._auth("acct-two", refresh_token="refresh-two")
        (self.codex_home / "auth.json").write_text(json.dumps(first), encoding="utf-8")

        result = self._run("add", "first")
        self.assertEqual(result.returncode, 0, result.stderr)

        result = self._run("add", "second", "--from", "-", stdin=json.dumps(second))
        self.assertEqual(result.returncode, 0, result.stderr)

        result = self._run("list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("first", result.stdout)
        self.assertIn("second", result.stdout)
        self.assertNotIn("ACCOUNT ID", result.stdout)
        self.assertNotIn("acct-one", result.stdout)
        self.assertNotIn("acct-two", result.stdout)
        self.assertNotIn("refresh-one", result.stdout)
        self.assertNotIn("refresh-two", result.stdout)

        result = self._run("use", "two")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("acct-two", result.stdout)
        active = json.loads((self.codex_home / "auth.json").read_text(encoding="utf-8"))
        self.assertEqual(active["tokens"]["account_id"], "acct-two")

    def test_list_shows_cached_quota_from_latest_session_log(self):
        auth = self._auth("acct-one")
        (self.codex_home / "auth.json").write_text(json.dumps(auth), encoding="utf-8")
        (self.codex_home / "accounts.json").write_text(
            json.dumps({"version": 1, "accounts": [{"label": "first", "auth": auth}]}),
            encoding="utf-8",
        )
        (self.sessions / "rollout.jsonl").write_text(
            "\n".join([
                json.dumps({
                    "timestamp": "2026-06-15T00:00:00Z",
                    "payload": {
                        "rate_limits": {
                            "primary": {
                                "used_percent": 41,
                                "window_minutes": 300,
                                "resets_at": 1781523251,
                            },
                            "secondary": {
                                "used_percent": 9,
                                "window_minutes": 10080,
                                "resets_at": 1781867601,
                            },
                            "plan_type": "unknown",
                        }
                    },
                })
            ]),
            encoding="utf-8",
        )

        result = self._run("list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("5H:41%/W:9%", result.stdout)
        self.assertIn("RESET TIME", result.stdout)
        self.assertIn("5H:", result.stdout)
        self.assertIn("/W:", result.stdout)

    def test_codex_wrapper_routes_account_commands_and_preserves_native_commands(self):
        auth = self._auth("acct-one")
        (self.codex_home / "auth.json").write_text(json.dumps(auth), encoding="utf-8")
        (self.codex_home / "accounts.json").write_text(
            json.dumps({"version": 1, "accounts": [{"label": "first", "auth": auth}]}),
            encoding="utf-8",
        )

        result = self._run_wrapper("account", "list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("first", result.stdout)
        self.assertNotIn("REAL_CODEX", result.stdout)

        result = self._run_wrapper("exec", "hello")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("REAL_CODEX:exec hello", result.stdout)


if __name__ == "__main__":
    unittest.main()
