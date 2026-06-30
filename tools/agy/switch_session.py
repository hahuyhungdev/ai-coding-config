import os
import sys
import signal
from pathlib import Path

# Ensure tools/agy is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from switch import rotate_account, generate_quota_rollover
from utils import AGY_DIR

def kill_ancestor_agy_bin():
    if os.environ.get("AGY_TESTING") == "1":
        return False
    pid = os.getpid()
    while pid > 1:
        try:
            # Read command and parent PID from proc fs
            with open(f"/proc/{pid}/stat", "r") as f:
                parts = f.read().split()
            ppid = int(parts[3])
            comm = parts[1].strip("()")

            # Check if this process is agy-bin
            if "agy-bin" in comm.lower():
                print(f"Found agy-bin ancestor (PID: {pid}). Terminating cleanly...")
                os.kill(pid, signal.SIGTERM)
                return True
            pid = ppid
        except Exception:
            break
    return False

def main():
    if len(sys.argv) > 1:
        target = sys.argv[1]
        print(f"🔄 Switching active account to target '{target}' manually...")
        from storage import load_accounts
        from switch import _write_active_account
        try:
            accounts = load_accounts()
        except Exception as e:
            print(f"❌ Failed to load accounts: {e}")
            sys.exit(1)

        found_idx = None
        if target.isdigit():
            idx = int(target) - 1
            if 0 <= idx < len(accounts):
                found_idx = idx
        else:
            for idx, acc in enumerate(accounts):
                email = acc.get("email") or acc.get("name") or ""
                if target.lower() in email.lower():
                    found_idx = idx
                    break
        if found_idx is not None:
            _write_active_account(accounts, found_idx)
            email = accounts[found_idx].get("email") or accounts[found_idx].get("name")
            print(f"✅ Switched active account to: {email}")
        else:
            print(f"❌ Error: Target '{target}' not found in accounts pool.")
            sys.exit(1)
    else:
        print("🔄 Initiating manual account rotation...")
        rotate_account()

    print("📝 Saving active conversation history...")
    generate_quota_rollover()

    # Touch the compaction signal file
    signal_file = Path(AGY_DIR) / ".compact_signal"
    signal_file.touch()

    # Terminate agy-bin to trigger the wrapper's restart loop
    if not kill_ancestor_agy_bin():
        # If running inside python directly or no ancestor found, print fallback
        print("⚠️ Ancestor agy-bin not found. Rollover configured on disk.")
        print("   Exiting normally. The new account will be used next time you run 'agy'.")

if __name__ == "__main__":
    main()
