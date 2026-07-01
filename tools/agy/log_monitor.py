import os
import sys
import time
import signal
import glob
from datetime import datetime, timedelta
from pathlib import Path

# Add tools/agy/ to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import AGY_DIR, LOG_DIR, is_provider_quota_error_line, session_state_path
from storage import load_accounts, write_accounts, active_account_index
from switch import select_replacement_index, _write_active_account, generate_quota_rollover

def get_newest_log_file(min_mtime=None):
    if not os.path.exists(LOG_DIR):
        return None
    files = [os.path.join(LOG_DIR, f) for f in os.listdir(LOG_DIR) if f.startswith("cli-") and f.endswith(".log")]
    if min_mtime is not None:
        files = [f for f in files if os.path.getmtime(f) >= min_mtime]
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

def get_live_quota_for_active_account(active_acc, active_idx):
    try:
        from pty_client import get_quota_via_pty
        from status_refresh import _quota_summary
        from parser import parse_quota_output
        import shutil
        import json
        
        email = active_acc.get("email") or active_acc.get("name")
        sandbox_dir = os.path.join(AGY_DIR, f"scratch/sandbox_active_check_{active_idx}")
        sandbox_gemini_dir = os.path.join(sandbox_dir, ".gemini/antigravity-cli")
        os.makedirs(sandbox_gemini_dir, exist_ok=True)
        
        sandbox_token_file = os.path.join(sandbox_gemini_dir, "antigravity-oauth-token")
        with open(sandbox_token_file, "w") as handle:
            json.dump(active_acc, handle)
            
        # Copy settings and installation_id
        for filename in ["settings.json", "installation_id"]:
            src = os.path.join(AGY_DIR, filename)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(sandbox_gemini_dir, filename))
                
        # Copy global cache directory if exists (holds ToS acceptance state)
        global_cache = os.path.join(AGY_DIR, "cache")
        if os.path.exists(global_cache):
            try:
                shutil.copytree(global_cache, os.path.join(sandbox_gemini_dir, "cache"))
            except Exception:
                pass
                
        output = get_quota_via_pty(email, sandbox_dir=sandbox_dir)
        
        try:
            shutil.rmtree(sandbox_dir)
        except:
            pass
            
        model_quotas = parse_quota_output(output)
        if model_quotas:
            quota_text, reset_text = _quota_summary(model_quotas)
            return quota_text, reset_text, model_quotas
    except Exception:
        pass
    return None, None, None

def check_active_account_quota():
    try:
        accounts = load_accounts()
        active_idx = active_account_index(accounts)
        if active_idx is None:
            return False
            
        active_acc = accounts[active_idx]
        email = active_acc.get("email") or active_acc.get("name")
        if not email:
            return False
            
        quota_text, reset_text, model_quotas = get_live_quota_for_active_account(active_acc, active_idx)
        if not quota_text:
            return False
            
        active_acc["quota"] = quota_text
        active_acc["reset_info"] = reset_text
        active_acc["model_quotas"] = model_quotas
        write_accounts(accounts, create_backup=False)
        
        from switch import is_account_blocked_or_low
        if is_account_blocked_or_low(active_acc, accounts):
            found_idx = select_replacement_index(accounts, active_idx)
            if found_idx is not None:
                _write_active_account(accounts, found_idx)
                try:
                    generate_quota_rollover()
                except:
                    pass
                try:
                    Path(session_state_path(".compact_signal", create_dir=True)).touch()
                except:
                    pass
                return True
    except Exception:
        pass
    return False

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
    try:
        proc_start_time = os.path.getmtime(f"/proc/{target_pid}")
    except:
        proc_start_time = time.time() - 5.0

    while time.time() - start_wait < 5.0:
        active_log = get_log_file_for_pid(target_pid)
        if active_log:
            break
        # Fallback to newest log, but only if modified after the target process started
        active_log = get_newest_log_file(min_mtime=proc_start_time - 2.0)
        if active_log:
            break
        time.sleep(0.1)

    if not active_log:
        sys.exit(0)

    try:
        state_log_file = Path(session_state_path("active_log_path", create_dir=True))
        state_log_file.write_text(active_log, encoding="utf-8")
        os.environ["AGY_SESSION_LOG_FILE"] = active_log
    except Exception:
        pass

    try:
        with open(active_log, "r", errors="ignore") as f:
            f.seek(0, 2)
            last_quota_check = time.time()
            while True:
                # Check if target process is still running
                try:
                    os.kill(target_pid, 0)
                except OSError:
                    # Process died, exit monitor
                    break

                # Periodic active quota threshold check (every 60 seconds)
                if time.time() - last_quota_check >= 60.0:
                    last_quota_check = time.time()
                    if check_active_account_quota():
                        print("\n⚠️ Active account quota dropped below threshold.")
                        print("♻️ Initiating automatic context compaction and account rotation...")
                        sys.stdout.flush()
                        try:
                            os.kill(target_pid, signal.SIGTERM)
                        except OSError:
                            pass
                        break

                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue

                if is_provider_quota_error_line(line):
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
                                Path(session_state_path(".compact_signal", create_dir=True)).touch()
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
