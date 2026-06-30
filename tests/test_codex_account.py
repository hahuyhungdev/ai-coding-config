import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import base64
import importlib.util
from unittest import mock
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

    def _run(self, *args, stdin=None, extra_env=None):
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env["CODEX_HOME"] = str(self.codex_home)
        env["PYTHONPYCACHEPREFIX"] = str(self.home / "pycache")
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            env=env,
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
        )

    def _run_wrapper(self, *args, stdin=None):
        real_codex = self.home / "codex-bin"
        real_codex.write_text(
            "\n".join([
                "#!/bin/sh",
                "if [ \"$1\" = \"login\" ]; then",
                "  mkdir -p \"$CODEX_HOME\"",
                "  cat > \"$CODEX_HOME/auth.json\" <<'EOF'",
                "{\"auth_mode\":\"chatgpt\",\"OPENAI_API_KEY\":null,\"tokens\":{\"access_token\":\"header.eyJlbWFpbCI6InNhbmRib3hAZXhhbXBsZS5jb20iLCJodHRwczovL2FwaS5vcGVuYWkuY29tL2F1dGgiOnsiY2hhdGdwdF9wbGFuX3R5cGUiOiJrMTIifX0.signature\",\"refresh_token\":\"login-temp-refresh\"},\"last_refresh\":\"2026-06-26T00:00:00Z\"}",
                "EOF",
                "  printf '%s\\n' 'LOGIN_TEMP_OK'",
                "  exit 0",
                "fi",
                "if [ -n \"${CODEX_ACCOUNT_LABEL:-}\" ]; then",
                "  mkdir -p \"$CODEX_HOME/sessions/2026/06/26\"",
                "  used=19",
                "  [ \"$CODEX_ACCOUNT_LABEL\" = \"k12-account\" ] && used=7",
                "  cat > \"$CODEX_HOME/sessions/2026/06/26/live.jsonl\" <<EOF",
                "{\"timestamp\":\"2026-06-26T00:00:00Z\",\"payload\":{\"rate_limits\":{\"primary\":{\"used_percent\":$used,\"resets_at\":1781523251},\"secondary\":{\"used_percent\":21,\"resets_at\":1781867601},\"plan_type\":\"k12\"}}}",
                "EOF",
                "  exit 0",
                "fi",
                "printf 'REAL_CODEX:%s\\n' \"$*\"",
            ]) + "\n",
            encoding="utf-8",
        )
        real_codex.chmod(0o755)
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env["CODEX_HOME"] = str(self.codex_home)
        env["CODEX_REAL_BIN"] = str(real_codex)
        env["PYTHONPYCACHEPREFIX"] = str(self.home / "pycache")
        return subprocess.run(
            [str(WRAPPER), *args],
            env=env,
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
        )

    def _jwt(self, claims):
        payload = base64.urlsafe_b64encode(
            json.dumps(claims, separators=(",", ":")).encode("utf-8")
        ).decode("utf-8").rstrip("=")
        return f"header.{payload}.signature"

    def _auth(self, account_id, refresh_token="refresh", plan=None, email=None):
        claims = {}
        if email:
            claims["email"] = email
        if plan:
            claims["https://api.openai.com/auth"] = {"chatgpt_plan_type": plan}
        return {
            "auth_mode": "chatgpt",
            "OPENAI_API_KEY": None,
            "tokens": {
                "access_token": self._jwt(claims) if claims else "not-a-jwt",
                "refresh_token": refresh_token,
                "account_id": account_id,
            },
            "last_refresh": "2026-06-15T00:00:00Z",
        }

    def _write_store(self, rows, active_auth):
        (self.codex_home / "auth.json").write_text(json.dumps(active_auth), encoding="utf-8")
        (self.codex_home / "accounts.json").write_text(
            json.dumps({"version": 1, "accounts": rows}),
            encoding="utf-8",
        )

    def _write_rate_limit(self, plan, primary_used, secondary_used, timestamp):
        existing = []
        log_path = self.sessions / "rollout.jsonl"
        if log_path.exists():
            existing = log_path.read_text(encoding="utf-8").splitlines()
        existing.append(json.dumps({
            "timestamp": timestamp,
            "payload": {
                "rate_limits": {
                    "primary": {
                        "used_percent": primary_used,
                        "window_minutes": 300,
                        "resets_at": 1781523251,
                    },
                    "secondary": {
                        "used_percent": secondary_used,
                        "window_minutes": 10080,
                        "resets_at": 1781867601,
                    },
                    "plan_type": plan,
                }
            },
        }))
        log_path.write_text("\n".join(existing), encoding="utf-8")

    def _load_script_module(self):
        spec = importlib.util.spec_from_file_location("codex_account_script", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_sandbox_tempdirs_ignore_cleanup_errors(self):
        module = self._load_script_module()
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(self.codex_home)}):
            with mock.patch.object(module.tempfile, "TemporaryDirectory") as temp_dir:
                temp_dir.return_value.__enter__.return_value = str(
                    self.codex_home / "tmp" / "codex-account-status-test"
                )
                temp_dir.return_value.__exit__.return_value = None

                with module.sandbox_tempdir("codex-account-status-") as tmp_dir:
                    self.assertIn("codex-account-status-test", tmp_dir)

                kwargs = temp_dir.call_args.kwargs
                self.assertEqual(kwargs["dir"], str(self.codex_home / "tmp"))
                self.assertTrue(kwargs["ignore_cleanup_errors"])

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

    def test_add_token_from_stdin_without_printing_secret(self):
        result = self._run("add-token", "pasted-account", "--from", "-", stdin="refresh-secret\n")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("pasted-account", result.stdout)
        self.assertNotIn("refresh-secret", result.stdout)
        store = json.loads((self.codex_home / "accounts.json").read_text(encoding="utf-8"))
        self.assertEqual(store["accounts"][0]["label"], "pasted-account")
        self.assertEqual(store["accounts"][0]["auth"]["auth_mode"], "chatgpt")
        self.assertEqual(store["accounts"][0]["auth"]["tokens"]["refresh_token"], "refresh-secret")
        self.assertNotIn("access_token", store["accounts"][0]["auth"]["tokens"])

    def test_add_token_accepts_json_token_payload(self):
        token_payload = {"refresh_token": "json-refresh-secret"}

        result = self._run("add-token", "json-account", "--from", "-", stdin=json.dumps(token_payload))

        self.assertEqual(result.returncode, 0, result.stderr)
        store = json.loads((self.codex_home / "accounts.json").read_text(encoding="utf-8"))
        self.assertEqual(store["accounts"][0]["label"], "json-account")
        self.assertEqual(store["accounts"][0]["auth"]["tokens"]["refresh_token"], "json-refresh-secret")

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
        self.assertIn("5H:59%/W:91%", result.stdout)
        self.assertIn("LEFT", result.stdout)
        self.assertIn("RESET", result.stdout)
        self.assertIn("5H:", result.stdout)
        self.assertIn("/W:", result.stdout)
        self.assertNotIn("PLAN", result.stdout)

    def test_status_text_uses_compact_table_without_plan_column(self):
        active = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        candidate = self._auth("acct-k12", refresh_token="refresh-k12", plan="k12")
        self._write_store(
            [
                {"label": "plus-account", "auth": active},
                {"label": "k12-account", "auth": candidate},
            ],
            active,
        )
        self._write_rate_limit("plus", primary_used=85, secondary_used=20, timestamp="2026-06-15T00:00:00Z")
        self._write_rate_limit("k12", primary_used=25, secondary_used=40, timestamp="2026-06-15T00:01:00Z")

        result = self._run("status", "--no-refresh")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Active: plus-account | low | left 5H:15%/W:80% | used 5H:85%/W:20%", result.stdout)
        self.assertIn("IDX  A  LABEL", result.stdout)
        self.assertIn("LEFT", result.stdout)
        self.assertNotIn("PLAN", result.stdout)
        self.assertNotIn("Active Codex account:", result.stdout)

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

    def test_codex_wrapper_routes_short_account_aliases_like_agy(self):
        active = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        candidate = self._auth("acct-k12", refresh_token="refresh-k12", plan="k12")
        self._write_store(
            [
                {"label": "plus-account", "auth": active},
                {"label": "k12-account", "auth": candidate},
            ],
            active,
        )
        self._write_rate_limit("plus", primary_used=85, secondary_used=20, timestamp="2026-06-15T00:00:00Z")
        self._write_rate_limit("k12", primary_used=25, secondary_used=40, timestamp="2026-06-15T00:01:00Z")

        result = self._run_wrapper("status", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("REAL_CODEX", result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["active"]["label"], "plus-account")
        self.assertTrue(payload["refreshed"])
        self.assertEqual(payload["source"], "live_codex_exec_rate_limits")
        self.assertEqual(payload["accounts"][0]["quota"], "5H:81%/W:79%")

        result = self._run_wrapper("rotate", "--dry-run", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("REAL_CODEX", result.stdout)
        rotate_payload = json.loads(result.stdout)
        self.assertFalse(rotate_payload["would_switch"])
        self.assertEqual(rotate_payload["reason"], "Active Codex account is healthy; use --force to rotate anyway")

        result = self._run_wrapper("rotate", "--force", "--dry-run", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("REAL_CODEX", result.stdout)
        self.assertEqual(json.loads(result.stdout)["target"]["label"], "k12-account")

        result = self._run_wrapper("list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("REAL_CODEX", result.stdout)
        self.assertIn("plus-account", result.stdout)

        result = self._run_wrapper("add-token", "pasted-account", stdin="refresh-secret\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("REAL_CODEX", result.stdout)
        self.assertNotIn("refresh-secret", result.stdout)

    def test_codex_wrapper_routes_reduced_aliases_and_guide(self):
        active = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        candidate = self._auth("acct-k12", refresh_token="refresh-k12", plan="k12")
        self._write_store(
            [
                {"label": "plus-account", "auth": active},
                {"label": "k12-account", "auth": candidate},
            ],
            active,
        )

        result = self._run_wrapper("check", "k12", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("REAL_CODEX", result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["refresh_target"], "k12")
        self.assertEqual(payload["accounts"][1]["quota"], "5H:93%/W:79%")

        result = self._run_wrapper("token", "short-token", stdin="refresh-secret\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("REAL_CODEX", result.stdout)
        self.assertNotIn("refresh-secret", result.stdout)

        result = self._run_wrapper("add", "active-copy")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("REAL_CODEX", result.stdout)
        self.assertIn("active-copy", result.stdout)

        result = self._run_wrapper("switch", "k12")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("REAL_CODEX", result.stdout)
        active_after = json.loads((self.codex_home / "auth.json").read_text(encoding="utf-8"))
        self.assertEqual(active_after["tokens"]["account_id"], "acct-k12")

        result = self._run_wrapper("guide")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("codex check [account]", result.stdout)
        self.assertIn("codex token [label]", result.stdout)

    def test_login_temp_adds_account_from_sandbox_auth_and_refreshes(self):
        active = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        self._write_store([{"label": "plus-account", "auth": active}], active)

        result = self._run_wrapper("login-temp", "sandbox-login", "--timeout", "5", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("LOGIN_TEMP_OK", result.stdout)
        payload = json.loads(result.stdout.split("LOGIN_TEMP_OK", 1)[1])
        self.assertEqual(payload["refresh_target"], "sandbox-login")
        store = json.loads((self.codex_home / "accounts.json").read_text(encoding="utf-8"))
        labels = [row["label"] for row in store["accounts"]]
        self.assertIn("sandbox-login", labels)

    def test_login_temp_uses_browser_login_by_default_and_device_auth_only_when_requested(self):
        active = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        self._write_store([{"label": "plus-account", "auth": active}], active)
        fake_codex = self.home / "codex-bin"
        calls_log = self.home / "login-calls.log"
        login_auth = json.dumps(
            self._auth("acct-login", refresh_token="refresh-login", plan="k12", email="temp@example.com")
        )
        fake_codex.write_text(
            "\n".join([
                "#!/bin/sh",
                "printf '%s\\n' \"$*\" >> \"$CODEX_LOGIN_CALLS_LOG\"",
                "mkdir -p \"$CODEX_HOME\"",
                "cat > \"$CODEX_HOME/auth.json\" <<'EOF'",
                login_auth,
                "EOF",
            ]) + "\n",
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)
        env = {
            "CODEX_REAL_BIN": str(fake_codex),
            "CODEX_LOGIN_CALLS_LOG": str(calls_log),
        }

        result = self._run("login-temp", "--no-refresh", "--json", extra_env=env)
        self.assertEqual(result.returncode, 0, result.stderr)

        result = self._run("login-temp", "--device-auth", "--no-refresh", "--json", extra_env=env)
        self.assertEqual(result.returncode, 0, result.stderr)

        self.assertEqual(calls_log.read_text(encoding="utf-8").splitlines(), [
            "login",
            "login --device-auth",
        ])

    def test_login_temp_creates_sandbox_codex_home_before_login(self):
        active = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        self._write_store([{"label": "plus-account", "auth": active}], active)
        fake_codex = self.home / "codex-bin"
        login_auth = json.dumps(
            self._auth("acct-login", refresh_token="refresh-login", plan="k12", email="temp@example.com")
        )
        fake_codex.write_text(
            "\n".join([
                "#!/bin/sh",
                "if [ \"$1\" = \"login\" ]; then",
                "  if [ ! -d \"$CODEX_HOME\" ]; then",
                "    printf '%s\\n' 'missing CODEX_HOME directory' >&2",
                "    exit 42",
                "  fi",
                "  case \"$CODEX_HOME\" in",
                "    \"$EXPECTED_SANDBOX_PREFIX\"/*) ;;",
                "    *) printf '%s\\n' \"sandbox outside CODEX_HOME tmp: $CODEX_HOME\" >&2; exit 43 ;;",
                "  esac",
                "  cat > \"$CODEX_HOME/auth.json\" <<'EOF'",
                login_auth,
                "EOF",
                "  exit 0",
                "fi",
                "mkdir -p \"$CODEX_HOME/sessions/2026/06/26\"",
                "cat > \"$CODEX_HOME/sessions/2026/06/26/live.jsonl\" <<'EOF'",
                "{\"timestamp\":\"2026-06-26T00:00:00Z\",\"payload\":{\"rate_limits\":{\"primary\":{\"used_percent\":8,\"resets_at\":1781523251},\"secondary\":{\"used_percent\":9,\"resets_at\":1781867601},\"plan_type\":\"k12\"}}}",
                "EOF",
            ]) + "\n",
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)

        result = self._run(
            "login-temp",
            "--timeout",
            "5",
            "--json",
            extra_env={
                "CODEX_REAL_BIN": str(fake_codex),
                "EXPECTED_SANDBOX_PREFIX": str(self.codex_home / "tmp"),
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("missing CODEX_HOME", result.stderr)
        self.assertNotIn("sandbox outside CODEX_HOME tmp", result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["refresh_target"], "temp@example.com")

    def test_reduced_commands_allow_omitted_labels_when_safe(self):
        active = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        self._write_store([{"label": "plus-account", "auth": active}], active)

        result = self._run_wrapper("login-temp", "--timeout", "5", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.split("LOGIN_TEMP_OK", 1)[1])
        self.assertEqual(payload["refresh_target"], "sandbox@example.com")
        store = json.loads((self.codex_home / "accounts.json").read_text(encoding="utf-8"))
        labels = [row["label"] for row in store["accounts"]]
        self.assertIn("sandbox@example.com", labels)

        result = self._run_wrapper("token", stdin="refresh-secret\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("pasted-token-", result.stdout)
        self.assertNotIn("refresh-secret", result.stdout)

    def test_account_help_uses_codex_account_program_name(self):
        result = self._run_wrapper("account", "-h")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: codex account", result.stdout)
        self.assertNotIn("usage: codex-account", result.stdout)

    def test_status_no_refresh_json_reports_active_health_from_cached_usage(self):
        active = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        candidate = self._auth("acct-k12", refresh_token="refresh-k12", plan="k12")
        self._write_store(
            [
                {"label": "plus-account", "auth": active},
                {"label": "k12-account", "auth": candidate},
            ],
            active,
        )
        self._write_rate_limit("plus", primary_used=85, secondary_used=20, timestamp="2026-06-15T00:00:00Z")
        self._write_rate_limit("k12", primary_used=25, secondary_used=40, timestamp="2026-06-15T00:01:00Z")

        result = self._run("status", "--no-refresh", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["active"]["label"], "plus-account")
        self.assertEqual(payload["active"]["status"], "low")
        self.assertFalse(payload["active"]["healthy"])
        self.assertEqual(payload["active"]["used_percent"], 85)
        self.assertEqual(payload["active"]["usage"], "5H:85%/W:20%")
        self.assertEqual(payload["active"]["quota"], "5H:15%/W:80%")
        self.assertEqual(payload["accounts"][1]["label"], "k12-account")
        self.assertEqual(payload["accounts"][1]["status"], "healthy")
        self.assertEqual(payload["accounts"][1]["usage"], "5H:25%/W:40%")
        self.assertEqual(payload["accounts"][1]["quota"], "5H:75%/W:60%")

    def test_status_json_refreshes_live_by_default(self):
        active = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        candidate = self._auth("acct-k12", refresh_token="refresh-k12", plan="k12")
        self._write_store(
            [
                {"label": "plus-account", "auth": active},
                {"label": "k12-account", "auth": candidate},
            ],
            active,
        )
        self._write_rate_limit("plus", primary_used=85, secondary_used=20, timestamp="2026-06-15T00:00:00Z")
        self._write_rate_limit("k12", primary_used=25, secondary_used=40, timestamp="2026-06-15T00:01:00Z")
        fake_codex = self.home / "codex-bin"
        calls_log = self.home / "codex-live-check.log"
        fake_codex.write_text(
            "\n".join([
                "#!/bin/sh",
                "printf '%s\\n' \"$CODEX_ACCOUNT_LABEL\" >> \"$CODEX_LIVE_CHECK_LOG\"",
                "mkdir -p \"$CODEX_HOME/sessions/2026/06/26\"",
                "used=19",
                "[ \"$CODEX_ACCOUNT_LABEL\" = \"k12-account\" ] && used=7",
                "cat > \"$CODEX_HOME/sessions/2026/06/26/live.jsonl\" <<EOF",
                "{\"timestamp\":\"2026-06-26T00:00:00Z\",\"payload\":{\"rate_limits\":{\"primary\":{\"used_percent\":$used,\"resets_at\":1781523251},\"secondary\":{\"used_percent\":21,\"resets_at\":1781867601},\"plan_type\":\"plus\"}}}",
                "EOF",
            ]) + "\n",
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)

        result = self._run(
            "status",
            "--json",
            extra_env={
                "CODEX_REAL_BIN": str(fake_codex),
                "CODEX_LIVE_CHECK_LOG": str(calls_log),
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["refreshed"])
        self.assertEqual(payload["source"], "live_codex_exec_rate_limits")
        self.assertEqual(payload["refresh_count"], 2)
        self.assertEqual(payload["accounts"][0]["quota"], "5H:81%/W:79%")
        self.assertEqual(payload["accounts"][1]["quota"], "5H:93%/W:79%")
        self.assertEqual(calls_log.read_text(encoding="utf-8").splitlines(), [
            "plus-account",
            "k12-account",
        ])

    def test_status_refresh_restores_active_auth_if_live_check_mutates_it(self):
        active = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        candidate = self._auth("acct-k12", refresh_token="refresh-k12", plan="k12")
        self._write_store(
            [
                {"label": "plus-account", "auth": active},
                {"label": "k12-account", "auth": candidate},
            ],
            active,
        )
        fake_codex = self.home / "codex-bin"
        candidate_json = json.dumps(candidate)
        fake_codex.write_text(
            "\n".join([
                "#!/bin/sh",
                "cat > \"$REAL_AUTH_PATH\" <<'EOF'",
                candidate_json,
                "EOF",
                "mkdir -p \"$CODEX_HOME/sessions/2026/06/26\"",
                "cat > \"$CODEX_HOME/sessions/2026/06/26/live.jsonl\" <<'EOF'",
                "{\"timestamp\":\"2026-06-26T00:00:00Z\",\"payload\":{\"rate_limits\":{\"primary\":{\"used_percent\":12,\"resets_at\":1781523251},\"secondary\":{\"used_percent\":34,\"resets_at\":1781867601},\"plan_type\":\"plus\"}}}",
                "EOF",
            ]) + "\n",
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)

        result = self._run(
            "status",
            "--json",
            extra_env={
                "CODEX_REAL_BIN": str(fake_codex),
                "REAL_AUTH_PATH": str(self.codex_home / "auth.json"),
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        active_after = json.loads((self.codex_home / "auth.json").read_text(encoding="utf-8"))
        self.assertEqual(active_after["tokens"]["account_id"], "acct-plus")

    def test_status_refresh_runs_codex_exec_and_caches_live_rate_limits(self):
        auth = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        self._write_store([{"label": "plus-account", "auth": auth}], auth)
        fake_codex = self.home / "codex-bin"
        calls_log = self.home / "codex-live-check.log"
        fake_codex.write_text(
            "\n".join([
                "#!/bin/sh",
                "printf '%s\\n' \"$CODEX_ACCOUNT_LABEL:$*\" >> \"$CODEX_LIVE_CHECK_LOG\"",
                "mkdir -p \"$CODEX_HOME/sessions/2026/06/26\"",
                "cat > \"$CODEX_HOME/sessions/2026/06/26/live.jsonl\" <<'EOF'",
                "{\"timestamp\":\"2026-06-26T00:00:00Z\",\"payload\":{\"rate_limits\":{\"primary\":{\"used_percent\":12,\"resets_at\":1781523251},\"secondary\":{\"used_percent\":34,\"resets_at\":1781867601},\"plan_type\":\"plus\"}}}",
                "EOF",
                "printf '%s\\n' '{\"type\":\"thread.started\"}'",
                "printf '%s\\n' '{\"type\":\"turn.completed\",\"usage\":{\"input_tokens\":1,\"output_tokens\":1}}'",
            ]) + "\n",
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)

        result = self._run(
            "status",
            "--refresh",
            "--json",
            extra_env={
                "CODEX_REAL_BIN": str(fake_codex),
                "CODEX_LIVE_CHECK_LOG": str(calls_log),
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["refreshed"])
        self.assertEqual(payload["active"]["quota"], "5H:88%/W:66%")
        self.assertEqual(payload["active"]["usage"], "5H:12%/W:34%")
        self.assertEqual(payload["active"]["used_percent"], 34)
        self.assertIn("plus-account:exec", calls_log.read_text(encoding="utf-8"))
        store = json.loads((self.codex_home / "accounts.json").read_text(encoding="utf-8"))
        snapshot = store["accounts"][0]["rate_limits_snapshot"]
        self.assertEqual(snapshot["rate_limits"]["primary"]["used_percent"], 12)

    def test_status_refresh_reports_useful_codex_exec_errors(self):
        auth = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        self._write_store([{"label": "plus-account", "auth": auth}], auth)
        fake_codex = self.home / "codex-bin"
        fake_codex.write_text(
            "\n".join([
                "#!/bin/sh",
                "printf '%s\\n' '{\"type\":\"error\",\"message\":\"auth expired\"}'",
                "exit 1",
            ]) + "\n",
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)

        result = self._run(
            "status",
            "--refresh",
            "--json",
            extra_env={"CODEX_REAL_BIN": str(fake_codex)},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["refresh_count"], 0)
        self.assertEqual(
            payload["refresh_errors"][0]["error"],
            "Codex exec exited 1 without rate limits: auth expired",
        )

    def test_status_refresh_marks_usage_limit_errors_as_exhausted_not_cached(self):
        auth = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        self._write_store([{"label": "plus-account", "auth": auth}], auth)
        self._write_rate_limit("plus", primary_used=12, secondary_used=18, timestamp="2026-06-15T00:00:00Z")
        fake_codex = self.home / "codex-bin"
        fake_codex.write_text(
            "\n".join([
                "#!/bin/sh",
                "printf '%s\\n' \"You've hit your usage limit. Try again at 2:02 PM.\" >&2",
                "exit 1",
            ]) + "\n",
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)

        result = self._run(
            "status",
            "--json",
            extra_env={"CODEX_REAL_BIN": str(fake_codex)},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["refresh_count"], 0)
        self.assertTrue(payload["active"]["stale"])
        self.assertEqual(payload["active"]["status"], "exhausted")
        self.assertFalse(payload["active"]["healthy"])
        self.assertEqual(payload["active"]["quota"], "0%")
        self.assertEqual(payload["active"]["usage"], "limit")
        self.assertEqual(payload["active"]["used_percent"], 100)
        self.assertIn("usage limit", payload["active"]["refresh_error"])

    def test_status_refresh_ignores_generic_stdin_notice_when_summarizing_errors(self):
        auth = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        self._write_store([{"label": "plus-account", "auth": auth}], auth)
        fake_codex = self.home / "codex-bin"
        fake_codex.write_text(
            "\n".join([
                "#!/bin/sh",
                "printf '%s\\n' 'Reading additional input from stdin...' >&2",
                "exit 1",
            ]) + "\n",
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)

        result = self._run(
            "status",
            "--refresh",
            "--json",
            extra_env={"CODEX_REAL_BIN": str(fake_codex)},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["refresh_errors"][0]["error"],
            "Codex exec exited 1 without rate limits",
        )

    def test_status_refresh_summarizes_pretty_json_error_codes(self):
        auth = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        self._write_store([{"label": "plus-account", "auth": auth}], auth)
        fake_codex = self.home / "codex-bin"
        fake_codex.write_text(
            "\n".join([
                "#!/bin/sh",
                "printf '%s\\n' '{' >&2",
                "printf '%s\\n' '  \"type\": \"error\",' >&2",
                "printf '%s\\n' '  \"code\": \"refresh_token_invalidated\"' >&2",
                "printf '%s\\n' '}' >&2",
                "exit 1",
            ]) + "\n",
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)

        result = self._run(
            "status",
            "--refresh",
            "--json",
            extra_env={"CODEX_REAL_BIN": str(fake_codex)},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["refresh_errors"][0]["error"],
            "Codex exec exited 1 without rate limits: refresh_token_invalidated",
        )

    def test_status_refresh_can_limit_to_one_account(self):
        active = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        candidate = self._auth("acct-k12", refresh_token="refresh-k12", plan="k12")
        self._write_store(
            [
                {"label": "plus-account", "auth": active},
                {"label": "k12-account", "auth": candidate},
            ],
            active,
        )
        fake_codex = self.home / "codex-bin"
        calls_log = self.home / "codex-live-check.log"
        fake_codex.write_text(
            "\n".join([
                "#!/bin/sh",
                "printf '%s\\n' \"$CODEX_ACCOUNT_LABEL\" >> \"$CODEX_LIVE_CHECK_LOG\"",
                "mkdir -p \"$CODEX_HOME/sessions/2026/06/26\"",
                "cat > \"$CODEX_HOME/sessions/2026/06/26/live.jsonl\" <<'EOF'",
                "{\"timestamp\":\"2026-06-26T00:00:00Z\",\"payload\":{\"rate_limits\":{\"primary\":{\"used_percent\":11,\"resets_at\":1781523251},\"secondary\":{\"used_percent\":22,\"resets_at\":1781867601},\"plan_type\":\"k12\"}}}",
                "EOF",
            ]) + "\n",
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)

        result = self._run(
            "status",
            "--refresh",
            "--account",
            "k12",
            "--json",
            extra_env={
                "CODEX_REAL_BIN": str(fake_codex),
                "CODEX_LIVE_CHECK_LOG": str(calls_log),
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["refresh_count"], 1)
        self.assertEqual(payload["refresh_target"], "k12")
        self.assertEqual(payload["accounts"][0]["quota"], "?")
        self.assertEqual(payload["accounts"][1]["quota"], "5H:89%/W:78%")
        self.assertEqual(payload["accounts"][1]["usage"], "5H:11%/W:22%")
        self.assertEqual(calls_log.read_text(encoding="utf-8").splitlines(), ["k12-account"])

    def test_status_refresh_timeout_option_fails_fast_without_traceback(self):
        auth = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        self._write_store([{"label": "plus-account", "auth": auth}], auth)
        fake_codex = self.home / "codex-bin"
        fake_codex.write_text("#!/bin/sh\nsleep 2\n", encoding="utf-8")
        fake_codex.chmod(0o755)

        result = self._run(
            "status",
            "--refresh",
            "--timeout",
            "0.1",
            "--json",
            extra_env={"CODEX_REAL_BIN": str(fake_codex)},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["refresh_count"], 0)
        self.assertIn("timed out after 0.1s", payload["refresh_errors"][0]["error"])
        self.assertNotIn("Traceback", result.stderr)

    def test_status_refresh_reports_progress_to_stderr(self):
        auth = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        self._write_store([{"label": "plus-account", "auth": auth}], auth)
        fake_codex = self.home / "codex-bin"
        fake_codex.write_text(
            "\n".join([
                "#!/bin/sh",
                "mkdir -p \"$CODEX_HOME/sessions/2026/06/26\"",
                "cat > \"$CODEX_HOME/sessions/2026/06/26/live.jsonl\" <<'EOF'",
                "{\"timestamp\":\"2026-06-26T00:00:00Z\",\"payload\":{\"rate_limits\":{\"primary\":{\"used_percent\":12,\"resets_at\":1781523251},\"secondary\":{\"used_percent\":34,\"resets_at\":1781867601},\"plan_type\":\"plus\"}}}",
                "EOF",
            ]) + "\n",
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)

        result = self._run(
            "status",
            "--refresh",
            "--json",
            extra_env={"CODEX_REAL_BIN": str(fake_codex)},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Refreshing Codex account 1/1: plus-account", result.stderr)

    def test_status_text_shortens_refresh_warnings(self):
        auth = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        self._write_store([{"label": "plus-account", "auth": auth}], auth)
        fake_codex = self.home / "codex-bin"
        fake_codex.write_text(
            "\n".join([
                "#!/bin/sh",
                "printf '%s\\n' '{\"type\":\"error\",\"message\":\"This is a very long Codex status refresh warning that includes a lot of diagnostic detail and a URL https://example.com/really/long/path/that/should/not/stretch/the/table\"}'",
                "exit 1",
            ]) + "\n",
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)

        result = self._run(
            "status",
            "--refresh",
            extra_env={"CODEX_REAL_BIN": str(fake_codex)},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        warning_lines = [line for line in result.stdout.splitlines() if line.startswith("Warning:")]
        self.assertEqual(len(warning_lines), 1)
        self.assertLessEqual(len(warning_lines[0]), 150)
        self.assertIn("...", warning_lines[0])
        self.assertNotIn("should/not/stretch/the/table", result.stdout)

    def test_status_refresh_places_sandbox_under_codex_home_tmp(self):
        auth = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        self._write_store([{"label": "plus-account", "auth": auth}], auth)
        fake_codex = self.home / "codex-bin"
        calls_log = self.home / "codex-live-check.log"
        fake_codex.write_text(
            "\n".join([
                "#!/bin/sh",
                "printf '%s\\n' \"$CODEX_HOME\" >> \"$CODEX_LIVE_CHECK_LOG\"",
                "mkdir -p \"$CODEX_HOME/sessions/2026/06/26\"",
                "cat > \"$CODEX_HOME/sessions/2026/06/26/live.jsonl\" <<'EOF'",
                "{\"timestamp\":\"2026-06-26T00:00:00Z\",\"payload\":{\"rate_limits\":{\"primary\":{\"used_percent\":12,\"resets_at\":1781523251},\"secondary\":{\"used_percent\":34,\"resets_at\":1781867601},\"plan_type\":\"plus\"}}}",
                "EOF",
            ]) + "\n",
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)

        result = self._run(
            "status",
            "--refresh",
            "--json",
            extra_env={
                "CODEX_REAL_BIN": str(fake_codex),
                "CODEX_LIVE_CHECK_LOG": str(calls_log),
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        logged_home = calls_log.read_text(encoding="utf-8").strip()
        self.assertTrue(
            logged_home.startswith(str(self.codex_home / "tmp") + os.sep),
            logged_home,
        )

    def test_status_refresh_ctrl_c_exits_without_python_traceback(self):
        auth = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        self._write_store([{"label": "plus-account", "auth": auth}], auth)
        fake_codex = self.home / "codex-bin"
        fake_codex.write_text("#!/bin/sh\nsleep 5\n", encoding="utf-8")
        fake_codex.chmod(0o755)
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env["CODEX_HOME"] = str(self.codex_home)
        env["CODEX_REAL_BIN"] = str(fake_codex)
        env["PYTHONPYCACHEPREFIX"] = str(self.home / "pycache")
        process = subprocess.Popen(
            [sys.executable, str(SCRIPT), "status", "--refresh", "--json"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(0.2)
        process.send_signal(signal.SIGINT)
        stdout, stderr = process.communicate(timeout=3)

        self.assertEqual(process.returncode, 130, stdout + stderr)
        self.assertIn("Interrupted Codex account command", stderr)
        self.assertNotIn("KeyboardInterrupt", stderr)
        self.assertNotIn("Traceback", stderr)

    def test_rotate_dry_run_selects_lowest_known_usage_without_mutating_auth(self):
        active = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        candidate = self._auth("acct-k12", refresh_token="refresh-k12", plan="k12")
        self._write_store(
            [
                {"label": "plus-account", "auth": active},
                {"label": "k12-account", "auth": candidate},
            ],
            active,
        )
        self._write_rate_limit("plus", primary_used=85, secondary_used=20, timestamp="2026-06-15T00:00:00Z")
        self._write_rate_limit("k12", primary_used=25, secondary_used=40, timestamp="2026-06-15T00:01:00Z")

        result = self._run("rotate", "--dry-run", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["would_switch"])
        self.assertEqual(payload["target"]["label"], "k12-account")
        active_after = json.loads((self.codex_home / "auth.json").read_text(encoding="utf-8"))
        self.assertEqual(active_after["tokens"]["account_id"], "acct-plus")

    def test_rotate_switches_to_best_known_candidate_and_backs_up_auth(self):
        active = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        candidate = self._auth("acct-k12", refresh_token="refresh-k12", plan="k12")
        unknown = self._auth("acct-unknown", refresh_token="refresh-unknown")
        self._write_store(
            [
                {"label": "plus-account", "auth": active},
                {"label": "k12-account", "auth": candidate},
                {"label": "unknown-account", "auth": unknown},
            ],
            active,
        )
        self._write_rate_limit("plus", primary_used=85, secondary_used=20, timestamp="2026-06-15T00:00:00Z")
        self._write_rate_limit("k12", primary_used=25, secondary_used=40, timestamp="2026-06-15T00:01:00Z")

        result = self._run("rotate", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["switched"])
        self.assertEqual(payload["target"]["label"], "k12-account")
        active_after = json.loads((self.codex_home / "auth.json").read_text(encoding="utf-8"))
        self.assertEqual(active_after["tokens"]["account_id"], "acct-k12")
        self.assertTrue(list(self.codex_home.glob("auth.json.bak-*")))

    def test_rotate_default_keeps_healthy_active_account(self):
        active = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        candidate = self._auth("acct-k12", refresh_token="refresh-k12", plan="k12")
        self._write_store(
            [
                {"label": "plus-account", "auth": active},
                {"label": "k12-account", "auth": candidate},
            ],
            active,
        )
        self._write_rate_limit("plus", primary_used=20, secondary_used=30, timestamp="2026-06-15T00:00:00Z")
        self._write_rate_limit("k12", primary_used=10, secondary_used=15, timestamp="2026-06-15T00:01:00Z")

        result = self._run("rotate", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["switched"])
        self.assertFalse(payload["would_switch"])
        self.assertEqual(payload["reason"], "Active Codex account is healthy; use --force to rotate anyway")
        active_after = json.loads((self.codex_home / "auth.json").read_text(encoding="utf-8"))
        self.assertEqual(active_after["tokens"]["account_id"], "acct-plus")

    def test_rotate_force_switches_even_when_active_account_is_healthy(self):
        active = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        candidate = self._auth("acct-k12", refresh_token="refresh-k12", plan="k12")
        self._write_store(
            [
                {"label": "plus-account", "auth": active},
                {"label": "k12-account", "auth": candidate},
            ],
            active,
        )
        self._write_rate_limit("plus", primary_used=20, secondary_used=30, timestamp="2026-06-15T00:00:00Z")
        self._write_rate_limit("k12", primary_used=10, secondary_used=15, timestamp="2026-06-15T00:01:00Z")

        result = self._run("rotate", "--force", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["switched"])
        self.assertEqual(payload["target"]["label"], "k12-account")
        active_after = json.loads((self.codex_home / "auth.json").read_text(encoding="utf-8"))
        self.assertEqual(active_after["tokens"]["account_id"], "acct-k12")

    def test_rotate_help_is_safe_and_does_not_switch_accounts(self):
        active = self._auth("acct-plus", refresh_token="refresh-plus", plan="plus")
        candidate = self._auth("acct-k12", refresh_token="refresh-k12", plan="k12")
        self._write_store(
            [
                {"label": "plus-account", "auth": active},
                {"label": "k12-account", "auth": candidate},
            ],
            active,
        )

        result = self._run("rotate", "--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: codex-account rotate", result.stdout)
        active_after = json.loads((self.codex_home / "auth.json").read_text(encoding="utf-8"))
        self.assertEqual(active_after["tokens"]["account_id"], "acct-plus")


if __name__ == "__main__":
    unittest.main()
