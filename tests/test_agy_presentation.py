import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


tools_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../tools/agy"))
if tools_dir not in sys.path:
    sys.path.insert(0, tools_dir)

import presentation
import storage


class TestAgyPresentation(unittest.TestCase):
    def test_active_account_email_matches_refresh_token(self):
        accounts = [
            {"email": "first@example.com", "token": {"refresh_token": "rt-1"}},
            {"email": "second@example.com", "token": {"refresh_token": "rt-2"}},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / "token.json"
            token_file.write_text('{"token": {"refresh_token": "rt-2"}}', encoding="utf-8")

            self.assertEqual(
                presentation.active_account_email(accounts, str(token_file)),
                "second@example.com",
            )

    def test_print_account_usage_table_uses_cached_model_quota(self):
        accounts = [
            {
                "email": "first@example.com",
                "token": {"refresh_token": "rt-1"},
                "model_quotas": {
                    "Gemini 3.5 Flash (High)": {
                        "five_hour_pct": 90,
                        "weekly_pct": 80,
                    },
                    "Claude Opus 4.6 (Thinking)": {
                        "five_hour_pct": 70,
                        "weekly_pct": 60,
                    },
                },
            }
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / "token.json"
            token_file.write_text('{"token": {"refresh_token": "rt-1"}}', encoding="utf-8")
            output = io.StringIO()

            with redirect_stdout(output):
                presentation.print_account_usage_table(accounts, str(token_file))

        rendered = output.getvalue()
        self.assertIn("first@example.com", rendered)
        self.assertIn("90%/80%", rendered)
        self.assertIn("70%/60%", rendered)
        self.assertIn("⭐", rendered)

    def test_storage_normalizes_and_upserts_token_payloads(self):
        token_obj, auth_method, email = storage.normalize_token_payload({
            "email": "first@example.com",
            "auth_method": "consumer",
            "token": {"refresh_token": "rt-1"},
        })
        accounts = []

        updated = storage.upsert_account_token(accounts, email, token_obj, auth_method)

        self.assertFalse(updated)
        self.assertEqual(accounts[0]["email"], "first@example.com")
        self.assertEqual(accounts[0]["token"]["refresh_token"], "rt-1")

        updated = storage.upsert_account_token(
            accounts,
            "first@example.com",
            {"refresh_token": "rt-2"},
            "consumer",
        )

        self.assertTrue(updated)
        self.assertEqual(accounts[0]["token"]["refresh_token"], "rt-2")


if __name__ == "__main__":
    unittest.main()
