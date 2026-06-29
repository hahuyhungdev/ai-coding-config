#!/usr/bin/env python3
import os
import sys
import json
import tempfile
import time
from datetime import datetime, timedelta

# Insert tools/agy path to import switch
tools_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tools/agy'))
if tools_dir not in sys.path:
    sys.path.insert(0, tools_dir)

import switch

def run_mock_test():
    print("🧪 Running mock account switch test...")
    with tempfile.TemporaryDirectory() as tmpdir:
        json_file = os.path.join(tmpdir, "accounts.json")
        token_file = os.path.join(tmpdir, "antigravity-oauth-token")
        log_dir = os.path.join(tmpdir, "log")
        os.makedirs(log_dir)

        # Mock the global file paths in switch module
        switch.JSON_FILE = json_file
        switch.TOKEN_FILE = token_file
        switch.AGY_DIR = tmpdir
        switch.LOG_DIR = log_dir

        # Setup 3 mock accounts:
        # - Account 1: Active, quota = 10% (Low quota <=30%)
        # - Account 2: Quota = 50% (Healthy)
        # - Account 3: Quota = 90% (Healthy, highest quota)
        mock_accounts = [
            {
                "email": "blocked_active@gmail.com",
                "token": {"refresh_token": "rt_blocked_active"},
                "quota": "10%",
                "status": "🟢 Ready",
                "model_quotas": {}
            },
            {
                "email": "healthy_medium@gmail.com",
                "token": {"refresh_token": "rt_healthy_medium"},
                "quota": "50%",
                "status": "🟢 Ready",
                "model_quotas": {}
            },
            {
                "email": "healthy_high@gmail.com",
                "token": {"refresh_token": "rt_healthy_high"},
                "quota": "90%",
                "status": "🟢 Ready",
                "model_quotas": {}
            }
        ]

        with open(json_file, "w") as f:
            json.dump(mock_accounts, f, indent=2)

        # Set Account 1 as active by saving it in token file
        with open(token_file, "w") as f:
            json.dump(mock_accounts[0], f, indent=2)

        print("\n--- Initial State ---")
        print(f"Active Account Token Email: {mock_accounts[0]['email']}")
        print(f"Active Account Quota: {mock_accounts[0]['quota']}")
        print("Candidate Accounts:")
        print(f"  - {mock_accounts[1]['email']}: {mock_accounts[1]['quota']}")
        print(f"  - {mock_accounts[2]['email']}: {mock_accounts[2]['quota']}")

        print("\n--- Triggering Proactive Auto-Switch ---")
        switch.auto_switch_account(quiet=False)

        print("\n--- Result State ---")
        with open(token_file, "r") as f:
            active_token = json.load(f)
        
        active_email = active_token.get("email")
        active_quota = active_token.get("quota")
        print(f"New Active Account Email: {active_email}")
        print(f"New Active Account Quota: {active_quota}")

        if active_email == "healthy_high@gmail.com":
            print("\n🎉 SUCCESS: Proactive switch to healthy_high worked!")
        else:
            print("\n❌ FAILURE: Proactive switch failed.")
            return

        # -------------------------------------------------------------
        # Test Case 2: Session Quota Exhaustion (429 Error) recovery
        # -------------------------------------------------------------
        print("\n=======================================================")
        print("🧪 Testing Session Quota Exhaustion Recovery (Post-Check)...")
        print("=======================================================")
        
        # Reset accounts:
        # - Account 2 (healthy_medium) is now active
        # - But during session, it hits a 429 quota error
        with open(token_file, "w") as f:
            json.dump(mock_accounts[1], f, indent=2)
            
        print(f"Current Active Account (Before failure): {mock_accounts[1]['email']}")
        
        # Write a mock recent log file that contains the 429 error
        log_path = os.path.join(log_dir, "cli-123.log")
        with open(log_path, "w") as f:
            f.write('''[I2606 16:37:00.123] label="Gemini 3.5 Flash (High)"
[W2606 16:37:05.456] API Error (code 429): RESOURCE_EXHAUSTED. Individual quota reached. Resets in 2h45m.
''')
        # Ensure log file modification time is fresh (recent)
        os.utime(log_path, (time.time(), time.time()))
        
        # Mock generate_quota_rollover so it doesn't fail trying to read actual brain dir
        switch.generate_quota_rollover = lambda: print("  📝 Generated rollover progress summary.")
        
        print("\n--- Triggering Post-Check Recovery ---")
        try:
            switch.post_check_and_switch()
        except SystemExit as e:
            exit_code = e.code
            print(f"Exit code from post_check_and_switch: {exit_code}")
            
        with open(token_file, "r") as f:
            new_active_token = json.load(f)
            
        print("\n--- Result State ---")
        print(f"New Active Account Email: {new_active_token.get('email')}")
        print(f"New Active Account Quota: {new_active_token.get('quota')}")
        
        with open(json_file, "r") as f:
            updated_accounts = json.load(f)
            
        print("\nUpdated Accounts Status in accounts.json:")
        for idx, acc in enumerate(updated_accounts):
            print(f"  [{idx+1}] {acc.get('email')}: status={acc.get('status')}, quota={acc.get('quota')}, blocked_until={acc.get('blocked_until')}")
            
        if new_active_token.get("email") == "healthy_high@gmail.com" and updated_accounts[1]["status"] == "🔴 Blocked":
            print("\n🎉 SUCCESS: The post-check successfully caught the 429 error, marked healthy_medium as Blocked, and auto-switched to healthy_high!")
        else:
            print("\n❌ FAILURE: Session recovery did not behave as expected.")
            return

        # -------------------------------------------------------------
        # Test Case 3: All accounts are blocked / low
        # -------------------------------------------------------------
        print("\n=======================================================")
        print("🧪 Testing Recovery when ALL accounts are Blocked / Low...")
        print("=======================================================")
        
        # Set all accounts' quota to 0% and status to Blocked
        with open(json_file, "r") as f:
            all_blocked_accs = json.load(f)
        for acc in all_blocked_accs:
            acc["quota"] = "0%"
            acc["status"] = "🔴 Blocked"
            acc["reset_info"] = "In 2h"
            acc["blocked_until"] = (datetime.now() + timedelta(hours=2)).isoformat()
        with open(json_file, "w") as f:
            json.dump(all_blocked_accs, f, indent=2)
            
        # Current active token is Account 3
        with open(token_file, "w") as f:
            json.dump(all_blocked_accs[2], f, indent=2)
            
        # Write another mock recent log file that contains the 429 error
        log_path2 = os.path.join(log_dir, "cli-456.log")
        with open(log_path2, "w") as f:
            f.write('''[I2606 16:40:00.123] label="Gemini 3.5 Flash (High)"
[W2606 16:40:05.456] API Error (code 429): RESOURCE_EXHAUSTED. Individual quota reached.
''')
        os.utime(log_path2, (time.time(), time.time()))

        print("\n--- Triggering Post-Check Recovery with All Accounts Blocked ---")
        try:
            switch.post_check_and_switch()
        except SystemExit as e:
            exit_code = e.code
            print(f"Exit code from post_check_and_switch: {exit_code}")
            if exit_code == 2:
                print("\n🎉 SUCCESS: The wrapper correctly aborted recovery with exit code 2 because all accounts were exhausted!")
            else:
                print(f"\n❌ FAILURE: Unexpected exit code {exit_code}.")

if __name__ == "__main__":
    run_mock_test()
