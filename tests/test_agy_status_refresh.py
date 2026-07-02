import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
AGY_TOOLS = REPO_ROOT / "tools" / "agy"

if str(AGY_TOOLS) not in sys.path:
    sys.path.insert(0, str(AGY_TOOLS))


def quota_screen(gemini_5h=100, gemini_weekly=100, claude_5h=100, claude_weekly=100):
    return f"""
GEMINI MODELS
  Weekly Limit
    [quota] {gemini_weekly}.00%
    Quota available
  Five Hour Limit
    [quota] {gemini_5h}.00%
    Quota available
CLAUDE AND GPT MODELS
  Weekly Limit
    [quota] {claude_weekly}.00%
    Quota available
  Five Hour Limit
    [quota] {claude_5h}.00%
    Quota available
"""


class TestAgyStatusRefresh(unittest.TestCase):
    def check_account_with_quota(self, output, settings=None):
        import status_refresh
        import switch

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            agy_dir = root / "agy"
            agy_dir.mkdir()
            settings_file = agy_dir / "settings.json"
            settings_file.write_text(json.dumps(settings or {}), encoding="utf-8")
            account = {
                "email": "account@example.com",
                "token": {"refresh_token": "rt-account"},
            }

            with patch.object(status_refresh, "AGY_DIR", str(agy_dir)), patch.object(
                status_refresh, "get_quota_via_pty", return_value=output
            ), patch.object(switch, "SETTINGS_FILE", str(settings_file)):
                return status_refresh._check_single_account(
                    0,
                    account,
                    [account],
                    {},
                    active_email=None,
                )

    def test_status_marks_weekly_quota_at_configured_threshold_as_low(self):
        result = self.check_account_with_quota(
            quota_screen(gemini_5h=100, gemini_weekly=45),
            settings={"threshold_weekly": 46},
        )

        self.assertEqual(result["status"], "🟡 Low")
        self.assertEqual(result["quota"], "5H:100%/W:45%")

    def test_status_keeps_account_ready_when_quota_is_above_thresholds(self):
        result = self.check_account_with_quota(
            quota_screen(gemini_5h=60, gemini_weekly=45),
            settings={"threshold_5h": 15, "threshold_weekly": 10},
        )

        self.assertEqual(result["status"], "🟢 Ready")
        self.assertEqual(result["quota"], "5H:60%/W:45%")

    def test_status_keeps_fully_exhausted_accounts_blocked(self):
        result = self.check_account_with_quota(
            quota_screen(gemini_5h=0, gemini_weekly=0, claude_5h=0, claude_weekly=0),
            settings={"threshold_5h": 15, "threshold_weekly": 10},
        )

        self.assertEqual(result["status"], "🔴 Blocked")
        self.assertEqual(result["quota"], "0%")


if __name__ == "__main__":
    unittest.main()
