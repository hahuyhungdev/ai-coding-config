import os
import sys
import time
from datetime import datetime, timedelta

# Ensure local imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from status_refresh import get_account_status
from switch import auto_switch_account


def run_check(refresh_status=True):
    if refresh_status:
        get_account_status()
    auto_switch_account(quiet=False)


def main(argv=None):
    import argparse
    from utils import AGY_DIR
    import fcntl

    # Lock file to prevent concurrent daemon executions
    os.makedirs(AGY_DIR, exist_ok=True)
    lock_file_path = os.path.join(AGY_DIR, "auto_rotate_daemon.lock")
    try:
        global _lock_file
        _lock_file = open(lock_file_path, "w")
        fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_file.write(str(os.getpid()))
        _lock_file.flush()
    except OSError:
        print("❌ Another instance of the auto-rotate daemon is already running.", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Auto-rotate daemon")
    parser.add_argument("--interval", type=int, default=300, help="Scan interval in seconds")
    parser.add_argument("--window", type=int, default=310, help="Scan window in seconds (ignored)")
    parser.add_argument("--no-refresh-status", action="store_true", help="Use cached account status instead of live quota refresh")
    args, _ = parser.parse_known_args(sys.argv[1:] if argv is None else argv)

    scan_interval = args.interval
    refresh_status = not args.no_refresh_status

    print(f"🚀 Auto-rotate daemon is running. Checking every {scan_interval}s. Press Ctrl+C to stop.")
    sys.stdout.flush()
    try:
        while True:
            try:
                run_check(refresh_status=refresh_status)
            except Exception as e:
                print(f"⚠️ [DAEMON] Error: {e}", file=sys.stderr)
            next_check = datetime.now() + timedelta(seconds=scan_interval)
            print(f"💤 Next check at {next_check.strftime('%H:%M:%S')}...", flush=True)
            time.sleep(scan_interval)
    except KeyboardInterrupt:
        print("\n🛑 Daemon stopped.")

if __name__ == "__main__":
    main()
