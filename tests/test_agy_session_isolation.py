import importlib
import json
import os
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


REPO_ROOT = Path(__file__).resolve().parents[1]
AGY_TOOLS = REPO_ROOT / "tools" / "agy"

if str(AGY_TOOLS) not in sys.path:
    sys.path.insert(0, str(AGY_TOOLS))


class TestAgySessionIsolation(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("AGY_SESSION_TOKEN_FILE", None)
        os.environ.pop("AGY_SESSION_LOG_FILE", None)

    def test_active_account_index_prefers_session_token_file(self):
        import storage

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            global_token = root / "global-token.json"
            session_token = root / "session-token.json"
            accounts = [
                {
                    "email": "account-one@example.com",
                    "token": {"refresh_token": "rt-one"},
                },
                {
                    "email": "account-two@example.com",
                    "token": {"refresh_token": "rt-two"},
                },
            ]

            global_token.write_text(json.dumps(accounts[1]), encoding="utf-8")
            session_token.write_text(json.dumps(accounts[0]), encoding="utf-8")

            old_token_file = storage.TOKEN_FILE
            try:
                storage.TOKEN_FILE = str(global_token)
                os.environ["AGY_SESSION_TOKEN_FILE"] = str(session_token)
                self.assertEqual(storage.active_account_index(accounts), 0)
            finally:
                storage.TOKEN_FILE = old_token_file

    def test_quota_log_check_prefers_session_log_over_newer_global_log(self):
        import switch

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            log_dir = root / "log"
            log_dir.mkdir()
            session_log = log_dir / "cli-session-a.log"
            other_log = log_dir / "cli-session-b.log"

            session_log.write_text(
                "\n".join(
                    [
                        'I0701 12:00:00.000 label="Gemini 3.5 Flash (High)"',
                        "E0701 12:00:01.000 error code=RESOURCE_EXHAUSTED quota exceeded resets in 2h",
                    ]
                ),
                encoding="utf-8",
            )
            other_log.write_text(
                'I0701 12:00:02.000 label="Claude Opus 4.6 (Thinking)"\n',
                encoding="utf-8",
            )

            now = time.time()
            os.utime(session_log, (now - 20, now - 20))
            os.utime(other_log, (now, now))

            old_log_dir = switch.LOG_DIR
            try:
                switch.LOG_DIR = str(log_dir)
                os.environ["AGY_SESSION_LOG_FILE"] = str(session_log)
                had_error, reset_time, blocked_model = switch.check_last_log_for_quota_error()
            finally:
                switch.LOG_DIR = old_log_dir

            self.assertTrue(had_error)
            self.assertEqual(reset_time, "In 2h")
            self.assertEqual(blocked_model, "gemini")


if __name__ == "__main__":
    unittest.main()
