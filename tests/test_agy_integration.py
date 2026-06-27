import os
import sys
import unittest
import shutil
import json
import time
import subprocess
from datetime import datetime, timedelta

# Set up tools/agy in path
tools_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tools/agy'))
sys.path.insert(0, tools_dir)

import storage
import utils
import switch
import auto_rotate_daemon
import parser
import status_refresh

# Use a scratch sandbox directory
SANDBOX_BASE = os.path.expanduser("~/.gemini/antigravity-cli/scratch/test_sandbox")

class TestAgyIntegration(unittest.TestCase):
    def setUp(self):
        # Create fresh sandbox directory for each test
        if os.path.exists(SANDBOX_BASE):
            shutil.rmtree(SANDBOX_BASE)
        os.makedirs(SANDBOX_BASE, exist_ok=True)
        os.environ["AGY_DIR_OVERRIDE"] = SANDBOX_BASE
        
        # Reset modules constants to pick up the new override
        utils.AGY_DIR = SANDBOX_BASE
        utils.JSON_FILE = os.path.join(SANDBOX_BASE, "accounts.json")
        utils.TOKEN_FILE = os.path.join(SANDBOX_BASE, "antigravity-oauth-token")
        utils.LOG_DIR = os.path.join(SANDBOX_BASE, "log")
        
        storage.AGY_DIR = SANDBOX_BASE
        storage.JSON_FILE = utils.JSON_FILE
        storage.TOKEN_FILE = utils.TOKEN_FILE
        
        switch.AGY_DIR = SANDBOX_BASE
        switch.JSON_FILE = utils.JSON_FILE
        switch.TOKEN_FILE = utils.TOKEN_FILE
        switch.LOG_DIR = utils.LOG_DIR
        switch.SETTINGS_FILE = os.path.join(SANDBOX_BASE, "settings.json")
        
        status_refresh.AGY_DIR = SANDBOX_BASE
        status_refresh.JSON_FILE = utils.JSON_FILE
        status_refresh.TOKEN_FILE = utils.TOKEN_FILE
        
        parser.JSON_FILE = utils.JSON_FILE
        parser.LOG_DIR = utils.LOG_DIR

    def tearDown(self):
        # Clean up sandbox
        if os.path.exists(SANDBOX_BASE):
            shutil.rmtree(SANDBOX_BASE)
        if "AGY_DIR_OVERRIDE" in os.environ:
            del os.environ["AGY_DIR_OVERRIDE"]

    def test_missing_config_files(self):
        # Verify behaviour with missing accounts.json
        self.assertEqual(storage.load_accounts(), [])
        
        # Verify behaviour with missing settings.json
        self.assertEqual(switch.load_rotation_policy(), "highest-quota")
        
        # Verify switch doesn't crash on missing accounts.json
        res = switch.auto_switch_account(quiet=True)
        self.assertEqual(res, "")

    def test_empty_config_files(self):
        # Write empty (0 bytes) files
        open(utils.JSON_FILE, "w").close()
        open(switch.SETTINGS_FILE, "w").close()
        open(os.path.join(SANDBOX_BASE, ".current_index"), "w").close()
        
        # Verify load_accounts returns [] instead of raising JSONDecodeError
        self.assertEqual(storage.load_accounts(), [])
        
        # Verify load_rotation_policy defaults to highest-quota
        self.assertEqual(switch.load_rotation_policy(), "highest-quota")
        
        # Verify auto_switch doesn't crash
        res = switch.auto_switch_account(quiet=True)
        self.assertEqual(res, "")

    def test_corrupted_config_files(self):
        # Write corrupted JSON
        with open(utils.JSON_FILE, "w") as f:
            f.write("{invalid json")
        with open(switch.SETTINGS_FILE, "w") as f:
            f.write("{invalid json")
            
        # Verify load_accounts raises JSONDecodeError
        with self.assertRaises(json.JSONDecodeError):
            storage.load_accounts()
            
        # Verify settings fallback to highest-quota
        self.assertEqual(switch.load_rotation_policy(), "highest-quota")

    def test_unknown_model_names_in_logs_and_fallback(self):
        # 1. Create a log file with an unknown GPT model name that failed
        os.makedirs(utils.LOG_DIR, exist_ok=True)
        log_path = os.path.join(utils.LOG_DIR, "cli-test.log")
        now = datetime.now()
        log_time_str = now.strftime("%m%d %H:%M:%S")
        
        with open(log_path, "w") as f:
            f.write(f"I{log_time_str} applyAuthResult email=test@gmail.com\n")
            f.write(f"I{log_time_str} label=\"GPT-OSS 120B (Medium)\"\n")
            f.write(f"E{log_time_str} RESOURCE_EXHAUSTED resets in 1h\n")
            
        # 2. Check if check_last_log_for_quota_error classifies GPT models correctly
        had_err, reset_str, blocked_model = switch.check_last_log_for_quota_error()
        self.assertTrue(had_err)
        self.assertEqual(blocked_model, "gpt")
        
        # 3. Verify choose_same_account_fallback returns "" for blocked Claude/GPT models
        acc = {
            "email": "test@gmail.com",
            "model_quotas": {
                "Gemini 3.5 Flash (High)": {"pct": 100},
                "Claude Opus 4.6 (Thinking)": {"pct": 100}
            }
        }
        res = switch.choose_same_account_fallback(acc, blocked_model="gpt")
        self.assertEqual(res, "")
        
        # 4. Verify get_model_pct returns 100 (default) for an unknown model
        self.assertEqual(utils.get_model_pct(acc["model_quotas"], "Unknown Model"), 100)

    def test_duplicate_tokens_handling(self):
        # Configure accounts where #1 and #2 have the same refresh token
        accounts = [
            {
                "email": "acc1@gmail.com",
                "token": {"refresh_token": "tokenA"},
                "quota": "100%",
                "status": "🟢 Ready"
            },
            {
                "email": "acc2@gmail.com",
                "token": {"refresh_token": "tokenA"},
                "quota": "100%",
                "status": "🟢 Ready"
            },
            {
                "email": "acc3@gmail.com",
                "token": {"refresh_token": "tokenB"},
                "quota": "100%",
                "status": "🟢 Ready"
            }
        ]
        with open(utils.JSON_FILE, "w") as f:
            json.dump(accounts, f)
            
        # Write active token as tokenA (index 0)
        with open(utils.TOKEN_FILE, "w") as f:
            json.dump(accounts[0], f)
            
        # Verify duplicate token detection
        dups = status_refresh.find_duplicate_refresh_tokens(accounts)
        self.assertIn(1, dups)
        self.assertEqual(dups[1], 0)  # index 1 is duplicate of index 0
        
        # Verify status check assigns "🟡 Dup" status to the duplicate
        res = status_refresh._check_single_account(1, accounts[1], accounts, dups, "acc1@gmail.com")
        self.assertEqual(res["status"], "🟡 Dup")
        self.assertEqual(res["quota"], "Same as #1")
        
        # Verify select_replacement_index skips the duplicate (index 1) and chooses index 2
        next_idx = switch.select_replacement_index(accounts, 0)
        self.assertEqual(next_idx, 2)  # skips index 1 (duplicate), selects index 2

    def test_concurrent_daemon_execution(self):
        # Verify that lock is acquired and prevents a second instance from starting
        import subprocess
        import signal
        
        pid_file = os.path.join(SANDBOX_BASE, "auto_rotate_daemon.pid")
        
        # Start daemon 1
        daemon1 = subprocess.Popen(
            [sys.executable, "-c", "import sys, os; sys.path.insert(0, sys.argv[1]); import auto_rotate_daemon; auto_rotate_daemon.main(['--interval', '10'])", tools_dir],
            env=os.environ,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Give it a brief moment to start and acquire lock
        time.sleep(0.5)
        
        # Verify PID file was created with the correct PID
        self.assertTrue(os.path.exists(pid_file), "PID file should be created by daemon")
        with open(pid_file, "r") as f:
            recorded_pid = int(f.read().strip())
        self.assertEqual(recorded_pid, daemon1.pid)
        
        # Run daemon 2 and verify it exits with 1
        daemon2 = subprocess.run(
            [sys.executable, "-c", "import sys, os; sys.path.insert(0, sys.argv[1]); import auto_rotate_daemon; auto_rotate_daemon.main(['--interval', '10'])", tools_dir],
            env=os.environ,
            capture_output=True,
            text=True
        )
        
        self.assertEqual(daemon2.returncode, 1)
        self.assertIn("Another instance of the auto-rotate daemon is already running", daemon2.stderr)
        
        # Terminate daemon 1 via SIGTERM — should clean up PID file
        daemon1.send_signal(signal.SIGTERM)
        daemon1.wait(timeout=5)
        daemon1.stdout.close()
        daemon1.stderr.close()
        
        # Give a moment for cleanup
        time.sleep(0.2)
        
        # PID file should be cleaned up after SIGTERM
        self.assertFalse(os.path.exists(pid_file), "PID file should be cleaned up after daemon stops")

    def test_expired_active_tokens_sync(self):
        # 1. Setup accounts on disk
        accounts = [
            {
                "email": "acc1@gmail.com",
                "token": {"refresh_token": "token1", "access_token": "old_access_token"},
                "auth_method": "consumer"
            },
            {
                "email": "acc2@gmail.com",
                "token": {"refresh_token": "token2", "access_token": "some_access_token"},
                "auth_method": "consumer"
            }
        ]
        with open(utils.JSON_FILE, "w") as f:
            json.dump(accounts, f)
            
        # 2. Setup active token with a refreshed/newer access token
        refreshed_active = {
            "email": "acc1@gmail.com",
            "token": {"refresh_token": "token1", "access_token": "new_refreshed_access_token"},
            "auth_method": "consumer"
        }
        with open(utils.TOKEN_FILE, "w") as f:
            json.dump(refreshed_active, f)
            
        # 3. Trigger account switch (which should sync first)
        switch._write_active_account(accounts, 1)
        
        # 4. Verify that accounts.json was updated with the new refreshed access token for acc1
        updated_accounts = storage.load_accounts()
        self.assertEqual(updated_accounts[0]["token"]["access_token"], "new_refreshed_access_token")

    def test_blocked_accounts_handling_and_expiration(self):
        now = datetime.now()
        accounts = [
            {
                "email": "acc1@gmail.com",
                "token": {"refresh_token": "token1"},
                "status": "🔴 Blocked",
                "blocked_until": (now + timedelta(hours=1)).isoformat() # Blocked for 1h
            },
            {
                "email": "acc2@gmail.com",
                "token": {"refresh_token": "token2"},
                "status": "🔴 Blocked",
                "blocked_until": (now - timedelta(minutes=5)).isoformat() # Block expired 5m ago
            },
            {
                "email": "acc3@gmail.com",
                "token": {"refresh_token": "token3"},
                "status": "🔴 Blocked",
                "last_checked": (now - timedelta(hours=3)).isoformat() # Blocked, no details, but checked 3h ago (default 2h expired)
            },
            {
                "email": "acc4@gmail.com",
                "token": {"refresh_token": "token4"},
                "status": "🔴 Blocked",
                "last_checked": (now - timedelta(minutes=15)).isoformat() # Blocked, checked 15m ago (not expired yet)
            },
            {
                "email": "acc5@gmail.com",
                "token": {"refresh_token": "token5"},
                "status": "🟢 Ready",
                "quota": "100%"
            }
        ]
        
        with open(utils.JSON_FILE, "w") as f:
            json.dump(accounts, f)
            
        # Test is_account_blocked_or_low
        self.assertTrue(switch.is_account_blocked_or_low(accounts[0], accounts)) # Still blocked (future blocked_until)
        self.assertFalse(switch.is_account_blocked_or_low(accounts[1], accounts)) # Expired blocked_until
        self.assertFalse(switch.is_account_blocked_or_low(accounts[2], accounts)) # Default 2h expired
        self.assertTrue(switch.is_account_blocked_or_low(accounts[3], accounts)) # Not expired 2h fallback
        self.assertFalse(switch.is_account_blocked_or_low(accounts[4], accounts)) # Healthy
        
        # Test selection / rotate: active is 0. Next candidates: 1, 2, 3, 4.
        # Healthy ones should be: 1, 2, 4. Under highest-quota, index 4 has 100% quota, so it is selected.
        next_idx = switch.select_replacement_index(accounts, 0)
        self.assertEqual(next_idx, 4)

if __name__ == "__main__":
    unittest.main()
