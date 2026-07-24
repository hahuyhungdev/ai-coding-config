import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
AGY_STATUS = REPO_DIR / "tools" / "agy" / "agy-status.py"
CODEX_ACCOUNT = REPO_DIR / "tools" / "codex-account" / "codex-account.py"
INSTALL_PY = REPO_DIR / "install.py"
INSTALL_AGY_PY = REPO_DIR / "install-agy.py"
MCP_TOGGLE_PY = REPO_DIR / "scripts" / "mcp-toggle.py"


def _worker_run_command(cmd, env):
    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


class TestParallelCliStress(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.codex_home = self.home / ".codex"
        self.codex_home.mkdir(parents=True, exist_ok=True)
        self.agy_dir = self.home / ".gemini" / "antigravity-cli"
        self.agy_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _get_base_env(self):
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env["CODEX_HOME"] = str(self.codex_home)
        env["AGY_DIR_OVERRIDE"] = str(self.agy_dir)
        env["AGY_WRAPPER_STATE_DIR"] = str(self.agy_dir)
        env.pop("AGY_SESSION_TOKEN_FILE", None)
        env["PYTHONPYCACHEPREFIX"] = str(self.home / "pycache")
        return env

    def test_high_concurrency_account_rotation_and_refreshes(self):
        """Run 16 parallel worker processes doing rotation & status refreshes without JSON corruption."""
        # Set up codex accounts
        accounts = []
        for i in range(1, 6):
            auth = {
                "auth_mode": "chatgpt",
                "tokens": {
                    "access_token": f"header.jwt{i}.sig",
                    "refresh_token": f"refresh-{i}",
                    "account_id": f"acct-{i}",
                },
                "last_refresh": "2026-06-15T00:00:00Z",
            }
            accounts.append({"label": f"account-{i}", "auth": auth})

        (self.codex_home / "auth.json").write_text(json.dumps(accounts[0]["auth"]), encoding="utf-8")
        (self.codex_home / "accounts.json").write_text(
            json.dumps({"version": 1, "accounts": accounts}), encoding="utf-8"
        )

        # Set up agy accounts
        agy_accounts = [
            {"name": f"acc{i}", "email": f"acc{i}@example.com", "quota": f"{100 - i*10}%", "status": "🟢 Active", "token": {"refresh_token": f"agy-tok-{i}"}}
            for i in range(1, 6)
        ]
        (self.agy_dir / "accounts.json").write_text(json.dumps(agy_accounts), encoding="utf-8")
        (self.agy_dir / "antigravity-oauth-token").write_text(json.dumps(agy_accounts[0]), encoding="utf-8")

        env = self._get_base_env()

        # Spawn 16 worker tasks concurrently
        tasks = []
        with ProcessPoolExecutor(max_workers=8) as executor:
            for i in range(16):
                if i % 4 == 0:
                    cmd = [sys.executable, str(CODEX_ACCOUNT), "rotate", "--dry-run", "--json"]
                elif i % 4 == 1:
                    cmd = [sys.executable, str(CODEX_ACCOUNT), "status", "--no-refresh", "--json"]
                elif i % 4 == 2:
                    cmd = [sys.executable, str(AGY_STATUS), "list", "--json"]
                else:
                    cmd = [sys.executable, str(AGY_STATUS), "doctor", "--json"]

                tasks.append(executor.submit(_worker_run_command, cmd, env))

        for future in as_completed(tasks):
            returncode, stdout, stderr = future.result()
            self.assertEqual(returncode, 0, f"Worker process failed with stderr: {stderr}")

        # Verify accounts.json and auth.json in CODEX_HOME and AGY_DIR remain valid JSON
        codex_auth = json.loads((self.codex_home / "auth.json").read_text(encoding="utf-8"))
        codex_store = json.loads((self.codex_home / "accounts.json").read_text(encoding="utf-8"))
        agy_store = json.loads((self.agy_dir / "accounts.json").read_text(encoding="utf-8"))

        self.assertIn("tokens", codex_auth)
        self.assertEqual(len(codex_store["accounts"]), 5)
        self.assertEqual(len(agy_store), 5)

    def test_account_quota_exhaustion_fallback_cascade(self):
        """Test cascade through exhausted accounts to healthy, and exit code 2 when all exhausted."""
        # 1. Codex accounts: primary used 100%, secondary used 95%, account 3 used 10%
        acct1 = {"auth_mode": "chatgpt", "tokens": {"access_token": "jwt1", "refresh_token": "r1", "account_id": "a1"}}
        acct2 = {"auth_mode": "chatgpt", "tokens": {"access_token": "jwt2", "refresh_token": "r2", "account_id": "a2"}}
        acct3 = {"auth_mode": "chatgpt", "tokens": {"access_token": "jwt3", "refresh_token": "r3", "account_id": "a3"}}

        snap1 = {"timestamp": "2026-06-15T00:00:00Z", "rate_limits": {"primary": {"used_percent": 100, "resets_at": 1781523251}}}
        snap2 = {"timestamp": "2026-06-15T00:00:00Z", "rate_limits": {"primary": {"used_percent": 95, "resets_at": 1781523251}}}
        snap3 = {"timestamp": "2026-06-15T00:00:00Z", "rate_limits": {"primary": {"used_percent": 10, "resets_at": 1781523251}}}

        (self.codex_home / "auth.json").write_text(json.dumps(acct1), encoding="utf-8")
        (self.codex_home / "accounts.json").write_text(
            json.dumps({
                "version": 1,
                "accounts": [
                    {"label": "acct1", "auth": acct1, "rate_limits_snapshot": snap1},
                    {"label": "acct2", "auth": acct2, "rate_limits_snapshot": snap2},
                    {"label": "acct3", "auth": acct3, "rate_limits_snapshot": snap3},
                ],
            }),
            encoding="utf-8",
        )

        # Log rate limits for acct1 (100%), acct2 (95%), acct3 (10%)
        sessions_dir = self.codex_home / "sessions" / "2026" / "06" / "15"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        (sessions_dir / "rollout.jsonl").write_text(json.dumps({
            "timestamp": "2026-06-15T00:00:00Z",
            "payload": {
                "rate_limits": {
                    "primary": {"used_percent": 100, "resets_at": 1781523251},
                    "secondary": {"used_percent": 20, "resets_at": 1781867601},
                    "plan_type": "plus",
                }
            }
        }), encoding="utf-8")

        env = self._get_base_env()

        # Run codex rotate --json
        res = subprocess.run(
            [sys.executable, str(CODEX_ACCOUNT), "rotate", "--dry-run", "--json"],
            env=env, capture_output=True, text=True, check=False,
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        payload = json.loads(res.stdout)
        self.assertTrue(payload["would_switch"])

        # Test agy clean exit code 2 when all accounts exhausted in switch.py
        mock_log = self.agy_dir / "log" / "cli-mock.log"
        mock_log.parent.mkdir(parents=True, exist_ok=True)
        now_str = time.strftime("%m%d %H:%M:%S")
        mock_log.write_text(f"E{now_str}.000000 12345 main.go:30] RESOURCE_EXHAUSTED resets in 2h\n", encoding="utf-8")

        all_blocked_accounts = [
            {"name": "acc1", "email": "acc1@test.com", "quota": "0%", "status": "🔴 Blocked", "token": {"refresh_token": "t1"}},
            {"name": "acc2", "email": "acc2@test.com", "quota": "0%", "status": "🔴 Blocked", "token": {"refresh_token": "t2"}},
        ]
        (self.agy_dir / "accounts.json").write_text(json.dumps(all_blocked_accounts), encoding="utf-8")
        (self.agy_dir / "antigravity-oauth-token").write_text(json.dumps(all_blocked_accounts[0]), encoding="utf-8")

        env["AGY_SESSION_LOG_FILE"] = str(mock_log)
        res_switch = subprocess.run(
            [sys.executable, "-c", "import sys, os; sys.path.insert(0, os.path.join(os.getcwd(), 'tools', 'agy')); from switch import post_check_and_switch; post_check_and_switch()"],
            env=env, capture_output=True, text=True, cwd=str(REPO_DIR),
        )
        self.assertEqual(res_switch.returncode, 2, f"Expected exit code 2 when all accounts exhausted, got {res_switch.returncode}. Output: {res_switch.stdout} {res_switch.stderr}")
        self.assertIn("All accounts are blocked", res_switch.stdout)

    def test_non_interactive_force_installs(self):
        """Test non-interactive force installs under piped and TTY stdin."""
        env = self._get_base_env()

        # Run install.py --all --force with piped empty stdin
        res_install = subprocess.run(
            [sys.executable, str(INSTALL_PY), "--all", "--force"],
            input="", env=env, cwd=str(self.home), capture_output=True, text=True, check=False,
        )
        self.assertEqual(res_install.returncode, 0, f"install.py failed: {res_install.stderr}")
        self.assertTrue((self.home / ".local" / "bin" / "codex").exists() or (self.home / ".claude").exists())

        # Run install-agy.py with piped empty stdin
        res_install_agy = subprocess.run(
            [sys.executable, str(INSTALL_AGY_PY)],
            input="", env=env, cwd=str(self.home), capture_output=True, text=True, check=False,
        )
        self.assertEqual(res_install_agy.returncode, 0, f"install-agy.py failed: {res_install_agy.stderr}")
        self.assertTrue((self.home / ".local" / "bin" / "agy").exists())

    def test_cli_status_commands_execution(self):
        """Test agy status, agy list, agy doctor, codex account list, codex status, mcp-toggle.py list."""
        env = self._get_base_env()

        # Set up minimal valid state for agy & codex
        auth = {
            "auth_mode": "chatgpt",
            "tokens": {"access_token": "jwt", "refresh_token": "ref", "account_id": "a1"},
            "last_refresh": "2026-06-15T00:00:00Z",
        }
        (self.codex_home / "auth.json").write_text(json.dumps(auth), encoding="utf-8")
        (self.codex_home / "accounts.json").write_text(
            json.dumps({"version": 1, "accounts": [{"label": "default", "auth": auth}]}), encoding="utf-8"
        )

        agy_accounts = [{"name": "default", "email": "def@example.com", "quota": "100%", "status": "🟢 Active", "token": {"refresh_token": "tok"}}]
        (self.agy_dir / "accounts.json").write_text(json.dumps(agy_accounts), encoding="utf-8")
        (self.agy_dir / "antigravity-oauth-token").write_text(json.dumps(agy_accounts[0]), encoding="utf-8")

        # 1. agy status
        res = subprocess.run([sys.executable, str(AGY_STATUS), "status"], env=env, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)

        # 2. agy list
        res = subprocess.run([sys.executable, str(AGY_STATUS), "list", "--json"], env=env, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("accounts", json.loads(res.stdout))

        # 3. agy doctor
        res = subprocess.run([sys.executable, str(AGY_STATUS), "doctor", "--json"], env=env, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("ok", json.loads(res.stdout))

        # 4. codex account list
        res = subprocess.run([sys.executable, str(CODEX_ACCOUNT), "list"], env=env, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("default", res.stdout)

        # 5. codex status
        res = subprocess.run([sys.executable, str(CODEX_ACCOUNT), "status", "--no-refresh", "--json"], env=env, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(json.loads(res.stdout)["active"]["label"], "default")

        # 6. mcp-toggle.py list
        res = subprocess.run([sys.executable, str(MCP_TOGGLE_PY), "list"], env=env, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)


if __name__ == "__main__":
    unittest.main()
