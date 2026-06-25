import os
import sys
import signal
from pathlib import Path

# Ensure tools/agy is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from switch import rotate_account, generate_quota_rollover
from utils import AGY_DIR

def kill_ancestor_agy_bin():
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
