import os
import sys
import time
import json
import shutil
import subprocess
from datetime import datetime, timedelta

# Paths
AGY_DIR = os.path.expanduser("~/.gemini/antigravity-cli")
JSON_FILE = os.path.join(AGY_DIR, "accounts.json")
TOKEN_FILE = os.path.join(AGY_DIR, "antigravity-oauth-token")
LOG_DIR = os.path.join(AGY_DIR, "log")
BACKUP_DIR = os.path.join(LOG_DIR, "backup_test_rotation")

def get_active_email():
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                token_data = json.load(f)
                return token_data.get("email") or token_data.get("name")
        except:
            pass
    return None

def reset_all_accounts_to_ready():
    # Clean up test log files first
    for name in ["cli-test.log", "cli-test-rotation.log"]:
        p = os.path.join(LOG_DIR, name)
        if os.path.exists(p):
            try:
                os.unlink(p)
            except:
                pass
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r") as f:
            accounts = json.load(f)
        for acc in accounts:
            acc["status"] = "🟢 Ready"
            acc["quota"] = "100%"
            if "blocked_until" in acc:
                del acc["blocked_until"]
            if "reset_info" in acc:
                del acc["reset_info"]
        with open(JSON_FILE, "w") as f:
            json.dump(accounts, f, indent=2)
        print("✅ Reset all accounts to 🟢 Ready and cleaned old logs.")

def simulate_quota_error(email):
    log_file = os.path.join(LOG_DIR, "cli-test-rotation.log")
    print(f"🔥 Simulating quota error for active account: {email}")
    content = (
        f"I0619 18:30:00.000000 12345 main.go:100] applyAuthResult email={email}\n"
        f"E0619 18:30:01.000000 12345 main.go:200] Error: RESOURCE_EXHAUSTED (code 429): Quota reached. Resets in 1h.\n"
    )
    with open(log_file, "w") as f:
        f.write(content)

def cleanup_simulated_error():
    log_file = os.path.join(LOG_DIR, "cli-test-rotation.log")
    if os.path.exists(log_file):
        try:
            os.unlink(log_file)
        except:
            pass

def main():
    print("🧪 Starting Daemon Rotation Concurrency & Stress Test...")
    
    # Create backup of all cli-*.log files to isolate test
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backed_up = []
    if os.path.exists(LOG_DIR):
        for f in os.listdir(LOG_DIR):
            if f.startswith("cli-") and f.endswith(".log") and f not in ["cli-test.log", "cli-test-rotation.log"]:
                src = os.path.join(LOG_DIR, f)
                dst = os.path.join(BACKUP_DIR, f)
                try:
                    shutil.move(src, dst)
                    backed_up.append(f)
                except Exception as e:
                    print(f"Warning: Failed to backup {f}: {e}")
                    
    # Spawn a local instance of the auto-rotate daemon with 1-second interval to run the test quickly
    daemon_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools/agy/auto_rotate_daemon.py")
    daemon_proc = None
    try:
        print("🚀 Spawning local daemon test instance with --interval 1...")
        daemon_proc = subprocess.Popen(
            [sys.executable, daemon_script, "--interval", "1", "--window", "5"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        reset_all_accounts_to_ready()
        
        # Wait for daemon to see status reset
        time.sleep(2)
        
        # We will simulate quota errors sequentially for 4 times to check if it rotates 4 accounts in a row
        for i in range(4):
            active_email = get_active_email()
            print(f"\n--- Rotation Step {i+1} ---")
            print(f"Current active account: {active_email}")
            
            # Write error log for the active account
            simulate_quota_error(active_email)
            
            # Wait up to 10 seconds for daemon to rotate
            rotated = False
            for _ in range(20):
                time.sleep(0.5)
                new_active = get_active_email()
                if new_active != active_email:
                    print(f"🎉 Success! Rotated from {active_email} to {new_active}")
                    cleanup_simulated_error()
                    # Wait 2 seconds for daemon to settle
                    time.sleep(2)
                    rotated = True
                    break
            if not rotated:
                print(f"❌ Error: Failed to rotate from {active_email} after 10 seconds.")
                cleanup_simulated_error()
                sys.exit(1)
                
        print("\n✅ Daemon Rotation stress test PASSED successfully!")
    finally:
        # Kill the spawned daemon process
        if daemon_proc is not None:
            print("🛑 Stopping local daemon test instance...")
            try:
                daemon_proc.terminate()
                daemon_proc.wait(timeout=2)
            except:
                try:
                    daemon_proc.kill()
                except:
                    pass
                    
        # Restore backups
        for f in backed_up:
            src = os.path.join(BACKUP_DIR, f)
            dst = os.path.join(LOG_DIR, f)
            if os.path.exists(src):
                try:
                    shutil.move(src, dst)
                except Exception as e:
                    print(f"Warning: Failed to restore {f}: {e}")
        if os.path.exists(BACKUP_DIR):
            try:
                os.rmdir(BACKUP_DIR)
            except:
                pass

if __name__ == "__main__":
    main()


