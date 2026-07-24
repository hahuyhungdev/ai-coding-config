import os
import sys
import json
import time
import shutil
import tempfile
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(REPO_DIR / "tools" / "agy"))

from switch import (
    select_replacement_index,
    is_account_blocked_or_low,
    is_account_blocked_only,
    has_model_quota,
    model_group_exhausted,
    auto_switch_account,
    post_check_and_switch,
    HIGHEST_QUOTA_POLICY,
)

def test_dynamic_rollover_simulation():
    """Simulate setup_test_rollover.py --dynamic and verify account rotation."""
    print("--- Running test_dynamic_rollover_simulation ---")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        agy_dir = tmp_path / ".gemini" / "antigravity-cli"
        log_dir = agy_dir / "log"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        accounts = [
            {"name": "acc1", "email": "acc1@test.com", "quota": "100%", "status": "🟢 Active", "token": {"refresh_token": "tok1"}, "model_quotas": {"Gemini 3.5 Flash (High)": {"pct": 100}}},
            {"name": "acc2", "email": "acc2@test.com", "quota": "90%", "status": "🟢 Active", "token": {"refresh_token": "tok2"}, "model_quotas": {"Gemini 3.5 Flash (High)": {"pct": 90}}},
            {"name": "acc3", "email": "acc3@test.com", "quota": "80%", "status": "🟢 Active", "token": {"refresh_token": "tok3"}, "model_quotas": {"Gemini 3.5 Flash (High)": {"pct": 80}}},
        ]
        accounts_file = agy_dir / "accounts.json"
        with open(accounts_file, "w") as f:
            json.dump(accounts, f, indent=2)
            
        token_file = agy_dir / "antigravity-oauth-token"
        with open(token_file, "w") as f:
            json.dump({"email": "acc1@test.com", "token": {"refresh_token": "tok1"}}, f)

        # Mock quota error log
        now = datetime.now()
        log_time_str = now.strftime("%m%d %H:%M:%S")
        mock_log = log_dir / "cli-mock-test.log"
        log_content = f"""I{log_time_str}.000000 12345 main.go:10] applyAuthResult email=acc1@test.com
I{log_time_str}.010000 12345 main.go:20] label="Gemini 3.5 Flash (High)"
E{log_time_str}.020000 12345 main.go:30] RESOURCE_EXHAUSTED resets in 2h30m
"""
        with open(mock_log, "w") as f:
            f.write(log_content)

        env = os.environ.copy()
        env.pop("AGY_SESSION_TOKEN_FILE", None)
        env["AGY_DIR_OVERRIDE"] = str(agy_dir)
        env["AGY_WRAPPER_STATE_DIR"] = str(agy_dir)
        env["AGY_SESSION_LOG_FILE"] = str(mock_log)
        env["HOME"] = str(tmp_path)
        
        res = subprocess.run(
            [sys.executable, "-c", "import sys, os; sys.path.insert(0, os.path.join(os.getcwd(), 'tools', 'agy')); from switch import post_check_and_switch; post_check_and_switch()"],
            capture_output=True, text=True, env=env, cwd=str(REPO_DIR)
        )
        
        print("post-check exit code:", res.returncode)
        print("post-check stdout:", res.stdout)
        print("post-check stderr:", res.stderr)
        
        # Verify active token moved to acc2 or acc3 (highest quota)
        with open(token_file, "r") as f:
            active_acc = json.load(f)
            
        print("Active account after rollover:", active_acc.get("email"))
        
        # acc1 should now be marked as blocked
        with open(accounts_file, "r") as f:
            updated_accounts = json.load(f)
            
        acc1_status = updated_accounts[0].get("status")
        print("acc1 status:", acc1_status)
        
        success = (res.returncode == 0 and ("Switched to:" in res.stdout or "Auto-switched account to" in res.stdout) and acc1_status == "🔴 Blocked" and active_acc.get("email") != "acc1@test.com")
        print("Dynamic rollover result:", "PASS" if success else "FAIL")
        return success

def test_all_accounts_exhausted_scenario():
    """Test behavior when ALL accounts are exhausted or blocked."""
    print("\n--- Running test_all_accounts_exhausted_scenario ---")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        agy_dir = tmp_path / ".gemini" / "antigravity-cli"
        log_dir = agy_dir / "log"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        accounts = [
            {"name": "acc1", "email": "acc1@test.com", "quota": "0%", "status": "🔴 Blocked", "model_quotas": {"Gemini 3.5 Flash (High)": {"pct": 0}}},
            {"name": "acc2", "email": "acc2@test.com", "quota": "0%", "status": "🔴 Blocked", "model_quotas": {"Gemini 3.5 Flash (High)": {"pct": 0}}},
            {"name": "acc3", "email": "acc3@test.com", "quota": "5%", "status": "🟡 Low", "model_quotas": {"Gemini 3.5 Flash (High)": {"pct": 5}}},
        ]
        accounts_file = agy_dir / "accounts.json"
        with open(accounts_file, "w") as f:
            json.dump(accounts, f, indent=2)
            
        token_file = agy_dir / "antigravity-oauth-token"
        with open(token_file, "w") as f:
            json.dump(accounts[0], f)

        env = os.environ.copy()
        env.pop("AGY_SESSION_TOKEN_FILE", None)
        env["AGY_DIR_OVERRIDE"] = str(agy_dir)
        env["AGY_WRAPPER_STATE_DIR"] = str(agy_dir)
        env["HOME"] = str(tmp_path)
        
        res = subprocess.run(
            [sys.executable, "-c", "import sys, os; sys.path.insert(0, os.path.join(os.getcwd(), 'tools', 'agy')); from switch import auto_switch_account; auto_switch_account()"],
            capture_output=True, text=True, env=env, cwd=str(REPO_DIR)
        )
        
        print("auto-switch stdout:", res.stdout)
        print("auto-switch stderr:", res.stderr)
        
        # When all accounts are blocked/low, replacement index should be None
        rep_idx = select_replacement_index(accounts, 0, policy=HIGHEST_QUOTA_POLICY, allow_best_effort=False)
        print("Replacement index when all low/blocked:", rep_idx)
        
        success = (rep_idx is None)
        print("All accounts exhausted scenario result:", "PASS" if success else "FAIL")
        return success

def test_per_model_quota_scenario():
    """Test model_group_exhausted and has_model_quota under partial quota exhaustion."""
    print("\n--- Running test_per_model_quota_scenario ---")
    
    acc_flash_low = {
        "model_quotas": {
            "Gemini 3.5 Flash (High)": {"pct": 0},
            "Gemini 3.1 Pro (High)": {"pct": 100},
        }
    }
    
    flash_has_quota = has_model_quota(acc_flash_low, "Gemini 3.5 Flash (High)", threshold=10)
    pro_has_quota = has_model_quota(acc_flash_low, "Gemini 3.1 Pro (High)", threshold=10)
    
    print("Flash has quota (>10%):", flash_has_quota, "(expected False)")
    print("Pro has quota (>10%):", pro_has_quota, "(expected True)")
    
    flash_exhausted = model_group_exhausted(acc_flash_low["model_quotas"], ["Gemini 3.5 Flash (High)"], threshold=10)
    print("Flash group exhausted:", flash_exhausted, "(expected True)")
    
    success = (not flash_has_quota and pro_has_quota and flash_exhausted)
    print("Per-model quota scenario result:", "PASS" if success else "FAIL")
    return success

if __name__ == "__main__":
    r1 = test_dynamic_rollover_simulation()
    r2 = test_all_accounts_exhausted_scenario()
    r3 = test_per_model_quota_scenario()
    
    all_pass = r1 and r2 and r3
    print(f"\nOverall Account Rotation Test Result: {'PASS' if all_pass else 'FAIL'}")
    sys.exit(0 if all_pass else 1)
