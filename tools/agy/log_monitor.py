import os
import sys
import time
import signal
import glob
from datetime import datetime, timedelta
from pathlib import Path

# Add tools/agy/ to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import AGY_DIR, LOG_DIR
from storage import load_accounts, write_accounts, active_account_index
from switch import select_replacement_index, _write_active_account, generate_quota_rollover

def get_newest_log_file():
    if not os.path.exists(LOG_DIR):
        return None
    files = [os.path.join(LOG_DIR, f) for f in os.listdir(LOG_DIR) if f.startswith("cli-") and f.endswith(".log")]
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]

def get_log_file_for_pid(pid):
    try:
        fd_path = f"/proc/{pid}/fd"
        if os.path.exists(fd_path):
            for fd in os.listdir(fd_path):
                try:
                    target = os.readlink(os.path.join(fd_path, fd))
                    if "cli-" in target and target.endswith(".log"):
                        return target
                except:
                    continue
    except:
        pass
    return None

def find_child_agy_bin(parent_pid):
    for pid_dir in glob.glob("/proc/[0-9]*"):
        try:
            pid = int(os.path.basename(pid_dir))
            with open(f"/proc/{pid}/stat", "r") as f:
                parts = f.read().split()
            ppid = int(parts[3])
            comm = parts[1].strip("()")
            if ppid == parent_pid and "agy-bin" in comm.lower():
                return pid
        except:
            continue
    return None

def main():
    if len(sys.argv) < 2:
        sys.exit(1)

    try:
        parent_pid = int(sys.argv[1])
    except ValueError:
        sys.exit(1)

    # Wait for the child agy-bin process to be created
    target_pid = None
    start_wait = time.time()
    while time.time() - start_wait < 5.0:
        target_pid = find_child_agy_bin(parent_pid)
        if target_pid:
            break
        time.sleep(0.1)

    if not target_pid:
        sys.exit(0)

    # Wait for the active log file to be created and bound to target_pid
    active_log = None
    start_wait = time.time()
    while time.time() - start_wait < 5.0:
        active_log = get_log_file_for_pid(target_pid)
        if active_log:
            break
        # Fallback to newest log if /proc/{target_pid}/fd is empty/denied
        active_log = get_newest_log_file()
        if active_log:
            if os.path.getmtime(active_log) > time.time() - 10:
                break
        time.sleep(0.1)

    if not active_log:
        sys.exit(0)

    try:
        with open(active_log, "r", errors="ignore") as f:
            f.seek(0, 2)
            while True:
                # Check if target process is still running
                try:
                    os.kill(target_pid, 0)
                except OSError:
                    # Process died, exit monitor
                    break

                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue

                line_lower = line.lower()
                if (
                    "resource_exhausted" in line_lower
                    or "quota exceeded" in line_lower
                    or "429" in line_lower
                    or "individual quota reached" in line_lower
                    or "too many tokens" in line_lower
                    or "rate limit" in line_lower
                ):
                    accounts = load_accounts()
                    active_idx = active_account_index(accounts)
                    if active_idx is not None:
                        active_acc = accounts[active_idx]
                        if active_acc.get("status") != "🔴 Blocked":
                            accounts[active_idx]["status"] = "🔴 Blocked"
                            accounts[active_idx]["quota"] = "0%"
                            accounts[active_idx]["reset_info"] = "In 2h"
                            accounts[active_idx]["blocked_until"] = (datetime.now() + timedelta(hours=2)).isoformat()
                            accounts[active_idx]["last_checked"] = datetime.now().isoformat()
                            write_accounts(accounts, create_backup=False)

                        found_idx = select_replacement_index(accounts, active_idx)
                        if found_idx is not None:
                            _write_active_account(accounts, found_idx)
                            try:
                                generate_quota_rollover()
                            except:
                                pass
                            try:
                                (Path(AGY_DIR) / ".compact_signal").touch()
                            except:
                                pass

                            # Kill the active agy-bin process
                            try:
                                os.kill(target_pid, signal.SIGTERM)
                            except OSError:
                                pass
                            break
    except Exception:
        pass

if __name__ == "__main__":
    main()
