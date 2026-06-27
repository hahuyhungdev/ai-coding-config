import os
import sys
import json
import unittest
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Load the modular agy package components
tools_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tools/agy'))
if tools_dir not in sys.path:
    sys.path.insert(0, tools_dir)

import switch
import utils

class TestSwitch(unittest.TestCase):
    def test_choose_same_account_fallback(self):
        # Case 1: Gemini blocked, Claude available
        acc = {
            "model_quotas": {
                utils.CLAUDE_FALLBACK_MODEL: {"pct": 100}
            }
        }
        res = switch.choose_same_account_fallback(acc, blocked_model="gemini")
        self.assertEqual(res, utils.CLAUDE_FALLBACK_MODEL)

        # Case 2: Claude blocked (should never fall back to Gemini)
        acc = {
            "model_quotas": {
                utils.GEMINI_FALLBACK_MODEL: {"pct": 100}
            }
        }
        res = switch.choose_same_account_fallback(acc, blocked_model="claude")
        self.assertEqual(res, "")

        # Case 3: No blocked model, Gemini available
        acc = {
            "model_quotas": {
                utils.GEMINI_FALLBACK_MODEL: {"pct": 100},
                utils.CLAUDE_FALLBACK_MODEL: {"pct": 100}
            }
        }
        res = switch.choose_same_account_fallback(acc)
        self.assertEqual(res, utils.GEMINI_FALLBACK_MODEL)

        # Case 4: No blocked model, Gemini exhausted, Claude available
        acc = {
            "model_quotas": {
                utils.GEMINI_FALLBACK_MODEL: {"pct": 0},
                utils.CLAUDE_FALLBACK_MODEL: {"pct": 80}
            }
        }
        res = switch.choose_same_account_fallback(acc)
        self.assertEqual(res, utils.CLAUDE_FALLBACK_MODEL)

    @patch("switch.get_remaining_reset_from_logs")
    def test_is_account_blocked_or_low(self, mock_reset_logs):
        mock_reset_logs.return_value = None

        # Case 1: Account with no email/name is blocked
        self.assertTrue(switch.is_account_blocked_or_low({}, []))

        # Case 2: Log check returns reset time -> blocked
        mock_reset_logs.return_value = "In 2h"
        self.assertTrue(switch.is_account_blocked_or_low({"email": "test@gmail.com"}, []))
        mock_reset_logs.return_value = None

        # Case 3: Cached status "🔴 Blocked", not expired
        acc = {
            "email": "test@gmail.com",
            "status": "🔴 Blocked",
            "reset_info": "In 1h 30m",
            "last_checked": (datetime.now() - timedelta(minutes=10)).isoformat()
        }
        self.assertTrue(switch.is_account_blocked_or_low(acc, []))

        # Case 4: Cached status "🔴 Blocked", expired
        acc = {
            "email": "test@gmail.com",
            "status": "🔴 Blocked",
            "reset_info": "In 30m",
            "last_checked": (datetime.now() - timedelta(minutes=45)).isoformat()
        }
        self.assertFalse(switch.is_account_blocked_or_low(acc, []))

        # Case 5: Quota is low (<=30%)
        acc = {
            "email": "test@gmail.com",
            "quota": "30%"
        }
        self.assertTrue(switch.is_account_blocked_or_low(acc, []))

        # Case 6: Quota is ready (>30%)
        acc = {
            "email": "test@gmail.com",
            "quota": "31%"
        }
        self.assertFalse(switch.is_account_blocked_or_low(acc, []))

        # Case 7: Blocked with blocked_until timestamp, not expired
        acc = {
            "email": "test@gmail.com",
            "status": "🔴 Blocked",
            "blocked_until": (datetime.now() + timedelta(minutes=30)).isoformat()
        }
        self.assertTrue(switch.is_account_blocked_or_low(acc, []))

        # Case 8: Blocked with blocked_until timestamp, expired
        acc = {
            "email": "test@gmail.com",
            "status": "🔴 Blocked",
            "blocked_until": (datetime.now() - timedelta(minutes=1)).isoformat()
        }
        self.assertFalse(switch.is_account_blocked_or_low(acc, []))

    def test_format_exact_reset_time(self):
        base_time = datetime(2026, 6, 15, 10, 0, 0) # Mon 10:00
        
        # Test basic In 2h 30m formatting
        res = utils.format_exact_reset_time("In 2h 30m", base_time=base_time)
        self.assertEqual(res, "Mon 12:30")
        
        # Test basic 97h formatting
        res = utils.format_exact_reset_time("97h", base_time=base_time)
        self.assertEqual(res, "Fri 11:00")
        
        # Test empty string returns empty
        self.assertEqual(utils.format_exact_reset_time(""), "")
        
        # Test invalid string returns original
        self.assertEqual(utils.format_exact_reset_time("invalid"), "invalid")

    @patch("switch.check_last_log_for_quota_error")
    @patch("switch.get_remaining_reset_from_logs")
    def test_auto_switch_account(self, mock_reset_logs, mock_quota_err):
        mock_reset_logs.return_value = None
        mock_quota_err.return_value = (False, "", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = os.path.join(tmpdir, "accounts.json")
            token_file = os.path.join(tmpdir, "token")

            # Mock switch paths
            switch.JSON_FILE = json_file
            switch.TOKEN_FILE = token_file
            switch.AGY_DIR = tmpdir

            # Case 1: JSON file doesn't exist
            self.assertEqual(switch.auto_switch_account(quiet=True), "")

            # Setup basic accounts pool
            accounts = [
                {
                    "email": "acc1@gmail.com",
                    "token": {"refresh_token": "rt1"},
                    "quota": "100%",
                    "status": "🟢 Ready",
                    "model_quotas": {}
                },
                {
                    "email": "acc2@gmail.com",
                    "token": {"refresh_token": "rt2"},
                    "quota": "100%",
                    "status": "🟢 Ready",
                    "model_quotas": {}
                }
            ]
            with open(json_file, "w") as f:
                json.dump(accounts, f)

            # Case 2: Token file doesn't exist -> initialize to first account
            self.assertEqual(switch.auto_switch_account(quiet=True), "")
            self.assertTrue(os.path.exists(token_file))
            if os.name == 'posix':
                self.assertEqual(os.stat(token_file).st_mode & 0o777, 0o600)
            with open(token_file, "r") as f:
                saved = json.load(f)
                self.assertEqual(saved["token"]["refresh_token"], "rt1")

            # Case 3: Current account is ready, no need to switch
            self.assertEqual(switch.auto_switch_account(quiet=True), "")
            with open(token_file, "r") as f:
                saved = json.load(f)
                self.assertEqual(saved["token"]["refresh_token"], "rt1")

            # Case 4: Current account is blocked -> switches circularly to acc2
            accounts[0]["status"] = "🔴 Blocked"
            accounts[0]["reset_info"] = "In 2h"
            accounts[0]["last_checked"] = datetime.now().isoformat()
            with open(json_file, "w") as f:
                json.dump(accounts, f)

            self.assertEqual(switch.auto_switch_account(quiet=True), "")
            with open(token_file, "r") as f:
                saved = json.load(f)
                self.assertEqual(saved["token"]["refresh_token"], "rt2")

            # Case 5: All accounts are blocked -> stay on current (acc2)
            accounts[1]["status"] = "🔴 Blocked"
            accounts[1]["reset_info"] = "In 2h"
            accounts[1]["last_checked"] = datetime.now().isoformat()
            with open(json_file, "w") as f:
                json.dump(accounts, f)

            self.assertEqual(switch.auto_switch_account(quiet=True), "")
            with open(token_file, "r") as f:
                saved = json.load(f)
                self.assertEqual(saved["token"]["refresh_token"], "rt2")

    def test_check_last_log_for_quota_error(self):
        import time
        orig_log_dir = switch.LOG_DIR
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                switch.LOG_DIR = tmpdir
                
                # Case 1: No log files
                res = switch.check_last_log_for_quota_error()
                self.assertEqual(res, (False, "", ""))
                
                # Case 2: Log file exists but is too old (>15 mins)
                log_path = os.path.join(tmpdir, "cli-old.log")
                with open(log_path, "w") as f:
                    f.write('''label="Gemini 3.5 Flash (High)"
RESOURCE_EXHAUSTED (code 429): Individual quota reached. Resets in 4h47m6s.
''')
                # set modification time to 20 minutes ago
                old_time = time.time() - 1200
                os.utime(log_path, (old_time, old_time))
                
                res = switch.check_last_log_for_quota_error()
                self.assertEqual(res, (False, "", ""))
                
                # Case 3: Recent log file with quota error and model override
                log_path_recent = os.path.join(tmpdir, "cli-recent.log")
                with open(log_path_recent, "w") as f:
                    f.write('''label="Gemini 3.5 Flash (High)"
RESOURCE_EXHAUSTED (code 429): Individual quota reached. Resets in 4h47m6s.
''')
                recent_time = time.time() - 10
                os.utime(log_path_recent, (recent_time, recent_time))
                
                res = switch.check_last_log_for_quota_error()
                self.assertEqual(res, (True, "In 4h47m6s", "gemini"))

                # Case 4: Recent log file with "Rate limit" and no "Resets in"
                with open(log_path_recent, "w") as f:
                    f.write('''label="Claude Opus 4.6 (Thinking)"
Rate limit reached on model
''')
                os.utime(log_path_recent, (recent_time, recent_time))
                
                res = switch.check_last_log_for_quota_error()
                self.assertEqual(res, (True, "", "claude"))
        finally:
            switch.LOG_DIR = orig_log_dir

    def test_generate_quota_rollover(self):
        # Backup existing .agy_progress.md if it exists
        progress_path = ".agy_progress.md"
        backup_content = None
        if os.path.exists(progress_path):
            with open(progress_path, "r", encoding="utf-8") as f:
                backup_content = f.read()
            os.unlink(progress_path)
            
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                with patch("os.path.expanduser") as mock_expanduser:
                    mock_expanduser.return_value = tmpdir
                    
                    # Create session directory
                    session_dir = os.path.join(tmpdir, "session-123")
                    os.makedirs(session_dir)
                    
                    # Create logs directory
                    logs_dir = os.path.join(session_dir, ".system_generated/logs")
                    os.makedirs(logs_dir)
                    
                    # Write transcript.jsonl
                    transcript_path = os.path.join(logs_dir, "transcript.jsonl")
                    with open(transcript_path, "w", encoding="utf-8") as f:
                        f.write(json.dumps({"type": "USER_INPUT", "content": "<USER_REQUEST>How to compile?</USER_REQUEST>"}) + "\n")
                        f.write(json.dumps({"type": "PLANNER_RESPONSE", "content": "You run make command."}) + "\n")
                        f.write(json.dumps({"type": "USER_INPUT", "content": "<USER_REQUEST>It failed with error.</USER_REQUEST>"}) + "\n")
                        
                    switch.generate_quota_rollover()
                    
                    # Verify .agy_progress.md contents
                    self.assertTrue(os.path.exists(progress_path))
                    with open(progress_path, "r", encoding="utf-8") as pf:
                        content = pf.read().strip()
                    
                    self.assertIn("User: How to compile?", content)
                    self.assertIn("Assistant: You run make command.", content)
                    self.assertIn("User: It failed with error.", content)
        finally:
            # Cleanup and restore
            if os.path.exists(progress_path):
                os.unlink(progress_path)
            if backup_content is not None:
                with open(progress_path, "w", encoding="utf-8") as f:
                    f.write(backup_content)

    @patch("switch.check_last_log_for_quota_error")
    @patch("switch.get_remaining_reset_from_logs")
    def test_auto_switch_uses_round_robin_health_gate_by_default(self, mock_reset_logs, mock_quota_err):
        mock_reset_logs.return_value = None
        mock_quota_err.return_value = (False, "", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = os.path.join(tmpdir, "accounts.json")
            token_file = os.path.join(tmpdir, "token")

            switch.JSON_FILE = json_file
            switch.TOKEN_FILE = token_file
            switch.AGY_DIR = tmpdir
            switch.SETTINGS_FILE = os.path.join(tmpdir, "settings.json")

            accounts = [
                {
                    "email": "acc1@gmail.com",
                    "token": {"refresh_token": "rt1"},
                    "quota": "0%",
                    "status": "🔴 Blocked",
                    "model_quotas": {}
                },
                {
                    "email": "acc2@gmail.com",
                    "token": {"refresh_token": "rt2"},
                    "quota": "50%",
                    "status": "🟢 Ready",
                    "model_quotas": {}
                },
                {
                    "email": "acc3@gmail.com",
                    "token": {"refresh_token": "rt3"},
                    "quota": "90%",
                    "status": "🟢 Ready",
                    "model_quotas": {}
                }
            ]
            with open(json_file, "w") as f:
                json.dump(accounts, f)

            with open(token_file, "w") as f:
                json.dump(accounts[0], f)

            self.assertEqual(switch.auto_switch_account(quiet=True), "")
            with open(token_file, "r") as f:
                saved = json.load(f)
                self.assertEqual(saved["token"]["refresh_token"], "rt2")

    @patch("switch.check_last_log_for_quota_error")
    @patch("switch.get_remaining_reset_from_logs")
    def test_round_robin_skips_low_candidates(self, mock_reset_logs, mock_quota_err):
        mock_reset_logs.return_value = None
        mock_quota_err.return_value = (False, "", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = os.path.join(tmpdir, "accounts.json")
            token_file = os.path.join(tmpdir, "token")

            switch.JSON_FILE = json_file
            switch.TOKEN_FILE = token_file
            switch.AGY_DIR = tmpdir
            switch.SETTINGS_FILE = os.path.join(tmpdir, "settings.json")

            accounts = [
                {"email": "acc1@gmail.com", "token": {"refresh_token": "rt1"}, "quota": "0%", "status": "🔴 Blocked"},
                {"email": "acc2@gmail.com", "token": {"refresh_token": "rt2"}, "quota": "20%", "status": "🟢 Ready"},
                {"email": "acc3@gmail.com", "token": {"refresh_token": "rt3"}, "quota": "70%", "status": "🟢 Ready"},
            ]
            with open(json_file, "w") as f:
                json.dump(accounts, f)
            with open(token_file, "w") as f:
                json.dump(accounts[0], f)

            self.assertEqual(switch.auto_switch_account(quiet=True), "")
            with open(token_file, "r") as f:
                saved = json.load(f)
                self.assertEqual(saved["token"]["refresh_token"], "rt3")

    @patch("switch.check_last_log_for_quota_error")
    @patch("switch.get_remaining_reset_from_logs")
    def test_round_robin_falls_back_to_best_low_quota_when_no_healthy_candidate(self, mock_reset_logs, mock_quota_err):
        mock_reset_logs.return_value = None
        mock_quota_err.return_value = (False, "", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = os.path.join(tmpdir, "accounts.json")
            token_file = os.path.join(tmpdir, "token")

            switch.JSON_FILE = json_file
            switch.TOKEN_FILE = token_file
            switch.AGY_DIR = tmpdir
            switch.SETTINGS_FILE = os.path.join(tmpdir, "settings.json")

            accounts = [
                {"email": "acc1@gmail.com", "token": {"refresh_token": "rt1"}, "quota": "0%", "status": "🔴 Blocked"},
                {"email": "acc2@gmail.com", "token": {"refresh_token": "rt2"}, "quota": "18%", "status": "🟢 Ready"},
                {"email": "acc3@gmail.com", "token": {"refresh_token": "rt3"}, "quota": "25%", "status": "🟢 Ready"},
            ]
            with open(json_file, "w") as f:
                json.dump(accounts, f)
            with open(token_file, "w") as f:
                json.dump(accounts[0], f)

            self.assertEqual(switch.auto_switch_account(quiet=True), "")
            with open(token_file, "r") as f:
                saved = json.load(f)
                self.assertEqual(saved["token"]["refresh_token"], "rt3")

    @patch("switch.get_remaining_reset_from_logs")
    def test_highest_quota_policy_remains_available_from_settings(self, mock_reset_logs):
        mock_reset_logs.return_value = None

        with tempfile.TemporaryDirectory() as tmpdir:
            switch.AGY_DIR = tmpdir
            switch.SETTINGS_FILE = os.path.join(tmpdir, "settings.json")
            with open(switch.SETTINGS_FILE, "w") as f:
                json.dump({"rotationPolicy": "highest-quota"}, f)

            accounts = [
                {"email": "acc1@gmail.com", "quota": "0%", "status": "🔴 Blocked"},
                {"email": "acc2@gmail.com", "quota": "50%", "status": "🟢 Ready"},
                {"email": "acc3@gmail.com", "quota": "90%", "status": "🟢 Ready"},
            ]

            self.assertEqual(switch.select_replacement_index(accounts, 0), 2)


if __name__ == "__main__":
    unittest.main()
