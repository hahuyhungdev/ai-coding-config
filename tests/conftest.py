import os
import shutil
import tempfile
import pytest

@pytest.fixture
def setup_test_env(monkeypatch):
    # Set up temporary test directory
    test_dir = tempfile.mkdtemp()
    
    # Paths for mock binary and config
    mock_bin_path = os.path.join(test_dir, "agy-bin")
    
    # Write mock agy-bin script
    mock_bin_content = """#!/usr/bin/env python3
import sys
import os
import json

# Create log directory if needed
agy_test_dir = os.environ.get("AGY_TEST_DIR")
if agy_test_dir:
    log_dir = os.path.join(agy_test_dir, "log")
    os.makedirs(log_dir, exist_ok=True)
    
    # If run with -p ping connection check...
    if len(sys.argv) > 1 and sys.argv[1] == "-p":
        # Write mock log file to trigger email detection
        log_file = os.path.join(log_dir, "cli-mock.log")
        with open(log_file, "w") as f:
            f.write("applyAuthResult: email=mock_detected_email@example.com\\n")
        sys.exit(0)

# Detect account email from token file in sandboxed HOME
home = os.environ.get("HOME")
email = ""
if home:
    token_path = os.path.join(home, ".gemini/antigravity-cli/antigravity-oauth-token")
    if os.path.exists(token_path):
        try:
            with open(token_path, "r") as f:
                token_data = json.load(f)
                email = token_data.get("email") or token_data.get("name") or ""
        except Exception:
            pass

# Output different quotas based on email to test sorting/switching
quota_pct = "80%"
if "acc1" in email:
    quota_pct = "20%"
elif "acc2" in email:
    quota_pct = "90%"
elif "acc3" in email:
    quota_pct = "50%"

# Print quota information matching get_quota_via_pty requirements
print("Gemini 3.5 Flash (High)")
print(f"  {quota_pct} remaining. Quota available. matches")
print("Gemini 3.5 Flash (Medium)")
print("  90% remaining.")

# Sleep or read stdin to allow pty client to write /exit
try:
    # Wait for /exit command from PTY client
    while True:
        line = sys.stdin.readline()
        if not line or "/exit" in line:
            break
except Exception:
    pass

sys.exit(0)
"""
    with open(mock_bin_path, "w") as f:
        f.write(mock_bin_content)
    os.chmod(mock_bin_path, 0o755)
    
    # Configure environment variables
    monkeypatch.setenv("AGY_TEST_DIR", test_dir)
    monkeypatch.setenv("AGY_TEST_REAL_BIN", mock_bin_path)
    monkeypatch.setenv("HOME", test_dir)
    
    yield test_dir
    
    # Clean up
    try:
        shutil.rmtree(test_dir)
    except OSError:
        pass
