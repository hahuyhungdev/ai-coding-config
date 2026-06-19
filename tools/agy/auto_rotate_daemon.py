import os
import sys
import time
from datetime import datetime, timedelta

# Ensure local imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from switch import auto_switch_account

def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Auto-rotate daemon")
    parser.add_argument("--interval", type=int, default=300, help="Scan interval in seconds")
    parser.add_argument("--window", type=int, default=310, help="Scan window in seconds (ignored)")
    args, _ = parser.parse_known_args(sys.argv[1:] if argv is None else argv)

    scan_interval = args.interval

    print(f"🚀 Auto-rotate daemon is running. Checking every {scan_interval}s. Press Ctrl+C to stop.")
    sys.stdout.flush()
    try:
        while True:
            try:
                auto_switch_account(quiet=False)
            except Exception as e:
                print(f"⚠️ [DAEMON] Error: {e}", file=sys.stderr)
            next_check = datetime.now() + timedelta(seconds=scan_interval)
            print(f"💤 Next check at {next_check.strftime('%H:%M:%S')}...", flush=True)
            time.sleep(scan_interval)
    except KeyboardInterrupt:
        print("\n🛑 Daemon stopped.")

if __name__ == "__main__":
    main()
