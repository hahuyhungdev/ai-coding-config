import os
import sys
import shutil
import json
import time
import subprocess
from datetime import datetime

# Setup paths
AGY_DIR = os.path.expanduser("~/.gemini/antigravity-cli")
TOKEN_FILE = os.path.join(AGY_DIR, "antigravity-oauth-token")
JSON_FILE = os.path.join(AGY_DIR, "accounts.json")

def configure_mock_state(account_email):
    # Find account index in json
    with open(JSON_FILE, "r") as f:
        accounts = json.load(f)

    # 1. Create mock session directory in brain
    mock_session_dir = os.path.join(AGY_DIR, "brain/mock_session_test")
    os.makedirs(os.path.join(mock_session_dir, ".system_generated/logs"), exist_ok=True)
    transcript_path = os.path.join(mock_session_dir, ".system_generated/logs/transcript.jsonl")

    mock_turns = [
        {"type": "USER_INPUT", "content": "<USER_REQUEST>Ai là người đẹp trai nhất thế giới?</USER_REQUEST>"},
        {"type": "PLANNER_RESPONSE", "content": "Tất nhiên là bạn rồi! Nhưng tài khoản của bạn vừa dính lỗi cạn quota, tôi đang chuẩn bị kích hoạt cơ chế rollover để cứu hộ đây."},
        {"type": "USER_INPUT", "content": "<USER_REQUEST>Thử chuyển tài khoản khác đi xem có giữ được câu hỏi này không nhé!</USER_REQUEST>"}
    ]

    with open(transcript_path, "w") as f:
        for turn in mock_turns:
            f.write(json.dumps(turn) + "\n")

    # Touch mock_session_dir to make it the newest
    os.utime(mock_session_dir, (time.time() + 10, time.time() + 10))

    # 2. Create mock log file with current timestamp
    now = datetime.now()
    log_time_str = now.strftime("%m%d %H:%M:%S")
    mock_log_path = os.path.join(AGY_DIR, "log/cli-mock-test.log")

    log_content = f"""I{log_time_str}.000000 12345 main.go:10] applyAuthResult email={account_email}@gmail.com
I{log_time_str}.010000 12345 main.go:20] label="Gemini 3.5 Flash (High)"
E{log_time_str}.020000 12345 main.go:30] RESOURCE_EXHAUSTED resets in 2h30m
"""

    with open(mock_log_path, "w") as f:
        f.write(log_content)
    os.utime(mock_log_path, (time.time() + 10, time.time() + 10))

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dynamic", action="store_true", help="Run dynamic rollover test")
    parser.add_argument(
        "--account-fragment",
        default=os.environ.get("AGY_TEST_ACCOUNT_FRAGMENT", ""),
        help="Account email/name fragment to use for the static rollover setup",
    )
    args = parser.parse_args()

    if not os.path.exists(JSON_FILE):
        print(f"❌ Error: accounts.json not found at {JSON_FILE}")
        return

    with open(JSON_FILE, "r") as f:
        accounts = json.load(f)

    # For dynamic test:
    # 1. Set active account to t01077949182 (Index 3) which is currently healthy
    # 2. Launch agy
    # 3. Wait 3 seconds, then write mock log blocking t01077949182 and mock session transcript
    # 4. User exits, post-check runs, detects block, switches to next healthy (e.g. hhhungdesigner or similar)
    if args.dynamic:
        target_email = "t01077949182"
        target_idx = None
        for idx, acc in enumerate(accounts):
            if (acc.get("email") or acc.get("name")) == target_email:
                target_idx = idx
                break

        if target_idx is None:
            # Fall back to first account
            target_idx = 0
            target_email = accounts[0].get("email") or accounts[0].get("name")

        print(f"1. Setting active account to '{target_email}'...")
        with open(TOKEN_FILE, "w") as f:
            json.dump(accounts[target_idx], f)
        os.chmod(TOKEN_FILE, 0o600)

        # Clear any old mock logs/sessions
        mock_log_path = os.path.join(AGY_DIR, "log/cli-mock-test.log")
        if os.path.exists(mock_log_path):
            os.remove(mock_log_path)

        print("2. Starting agy CLI session...")
        print("   -> Wait for the CLI to fully load.")
        print("   -> Once loaded, just type /exit (or press Ctrl+D) to trigger the rollover!")
        print("   -> Mock files will be created in the background in 4 seconds.")
        print("------------------------------------------------------------------------")

        # Fork and start mock writer in background
        pid = os.fork()
        if pid == 0:
            # Background process: wait 4 seconds, then write mock files
            time.sleep(4)
            configure_mock_state(target_email)
            os._exit(0)
        else:
            # Parent process: run agy wrapper interactively
            # This replaces the process with agy wrapper
            os.execvp("agy", ["agy"])
        return

    # Static test setup
    account_fragment = args.account_fragment.strip().lower()
    if not account_fragment:
        print("❌ Error: provide --account-fragment or AGY_TEST_ACCOUNT_FRAGMENT")
        return

    static_idx = None
    static_email = ""
    for idx, acc in enumerate(accounts):
        email = acc.get("email") or acc.get("name")
        if account_fragment in str(email).lower():
            static_idx = idx
            static_email = email
            break

    if static_idx is None:
        print("❌ Error: matching account not found in accounts.json")
        return

    print(f"1. Setting active account to '{static_email}'...")
    with open(TOKEN_FILE, "w") as f:
        json.dump(accounts[static_idx], f)
    os.chmod(TOKEN_FILE, 0o600)

    configure_mock_state(static_email)

    print("\n✅ Test environment configured successfully!")
    print("------------------------------------------------------------------------")
    print("👉 NOW, RUN THE FOLLOWING COMMAND IN YOUR TERMINAL:")
    print("   agy")
    print("------------------------------------------------------------------------")

if __name__ == "__main__":
    main()
