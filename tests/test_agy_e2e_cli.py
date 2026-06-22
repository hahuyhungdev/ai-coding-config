import os
import sys
import json
import subprocess
import time
import shutil
import signal
from datetime import datetime, timedelta
import pytest

def run_agy(args, stdin=None):
    cmd = [sys.executable, "tools/agy/agy-status.py"] + args
    res = subprocess.run(
        cmd,
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return res

def write_accounts_json(test_dir, accounts):
    json_path = os.path.join(test_dir, "accounts.json")
    with open(json_path, "w") as f:
        json.dump(accounts, f, indent=2)
    return json_path

def write_token_json(test_dir, token):
    token_path = os.path.join(test_dir, "antigravity-oauth-token")
    with open(token_path, "w") as f:
        json.dump(token, f, indent=2)
    return token_path

def setup_standard_accounts(test_dir):
    accounts = [
        {
            "email": "acc1@example.com",
            "token": {"refresh_token": "rt1"},
            "quota": "80%",
            "status": "🟢 Ready",
            "model_quotas": {}
        },
        {
            "email": "acc2@example.com",
            "token": {"refresh_token": "rt2"},
            "quota": "60%",
            "status": "🟢 Ready",
            "model_quotas": {}
        }
    ]
    write_accounts_json(test_dir, accounts)
    write_token_json(test_dir, accounts[0])
    return accounts

# Feature 1: agy status
def test_agy_status_live_refresh(setup_test_env):
    test_dir = setup_test_env
    setup_standard_accounts(test_dir)
    
    res = run_agy(["status"])
    assert res.returncode == 0
    assert "Checking status for acc1@example.com..." in res.stdout
    assert "Checking status for acc2@example.com..." in res.stdout
    assert "acc1@example.com" in res.stdout
    
    # Verify accounts.json was updated
    json_path = os.path.join(test_dir, "accounts.json")
    with open(json_path, "r") as f:
        updated = json.load(f)
    assert updated[0]["status"] == "🟢 Ready"

def test_agy_status_json_and_sort(setup_test_env):
    test_dir = setup_test_env
    accounts = [
        {
            "email": "acc1@example.com",
            "token": {"refresh_token": "rt1"},
            "quota": "20%",
            "status": "🟢 Ready"
        },
        {
            "email": "acc2@example.com",
            "token": {"refresh_token": "rt2"},
            "quota": "90%",
            "status": "🟢 Ready"
        }
    ]
    write_accounts_json(test_dir, accounts)
    write_token_json(test_dir, accounts[0])
    
    res = run_agy(["status", "--json"])
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["refreshed"] is True
    # Should sort by remaining quota: 90% (acc2) first, then 20% (acc1)
    assert "acc2" in data["accounts"][0]["email"]
    assert "acc1" in data["accounts"][1]["email"]

def test_agy_status_duplicate_tokens(setup_test_env):
    test_dir = setup_test_env
    accounts = [
        {
            "email": "acc1@example.com",
            "token": {"refresh_token": "rt_dup"},
            "quota": "80%",
            "status": "🟢 Ready"
        },
        {
            "email": "acc2@example.com",
            "token": {"refresh_token": "rt_dup"},
            "quota": "80%",
            "status": "🟢 Ready"
        }
    ]
    write_accounts_json(test_dir, accounts)
    write_token_json(test_dir, accounts[0])
    
    res = run_agy(["status", "--json"])
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["accounts"][1]["status"] == "🟡 Dup"
    assert "Same as #1" in data["accounts"][1]["quota"]

def test_agy_status_malformed_json(setup_test_env):
    test_dir = setup_test_env
    json_path = os.path.join(test_dir, "accounts.json")
    with open(json_path, "w") as f:
        f.write("invalid json")
    
    res = run_agy(["status"])
    assert res.returncode == 1
    assert "Error" in res.stderr

def test_agy_status_missing_token_file(setup_test_env):
    test_dir = setup_test_env
    accounts = [
        {
            "email": "acc1@example.com",
            "token": {"refresh_token": "rt1"},
            "quota": "80%",
            "status": "🟢 Ready"
        }
    ]
    write_accounts_json(test_dir, accounts)
    
    res = run_agy(["status"])
    assert res.returncode == 0
    assert "Checking status for acc1@example.com..." in res.stdout

def test_agy_status_empty_pool(setup_test_env):
    test_dir = setup_test_env
    write_accounts_json(test_dir, [])
    
    res = run_agy(["status"])
    assert res.returncode == 0  # get_account_status handles it, just nothing is done

def test_agy_status_garbage_pty_fallback(setup_test_env, monkeypatch):
    test_dir = setup_test_env
    setup_standard_accounts(test_dir)
    
    # Write garbage-emitting mock script
    garbage_bin = os.path.join(test_dir, "garbage-bin")
    with open(garbage_bin, "w") as f:
        f.write("#!/usr/bin/env python3\nimport sys\nprint('garbage output')\nsys.exit(0)\n")
    os.chmod(garbage_bin, 0o755)
    
    monkeypatch.setenv("AGY_TEST_REAL_BIN", garbage_bin)
    res = run_agy(["status", "--json"])
    assert res.returncode == 0
    data = json.loads(res.stdout)
    # Falling back because no quota screen keywords -> Ready / 100%
    assert data["accounts"][0]["status"] == "🟢 Ready"
    assert data["accounts"][0]["quota"] == "100%"

# Feature 2: agy account
def test_agy_account_commands(setup_test_env):
    test_dir = setup_test_env
    setup_standard_accounts(test_dir)
    
    # list
    res = run_agy(["account", "list"])
    assert res.returncode == 0
    assert "acc1@example.com" in res.stdout
    assert "acc2@example.com" in res.stdout
    
    # current
    res = run_agy(["account", "current"])
    assert res.returncode == 0
    assert "acc1@example.com" in res.stdout
    
    # use
    res = run_agy(["account", "use", "2"])
    assert res.returncode == 0
    assert "Switched active account to acc2" in res.stdout
    
    # rename
    res = run_agy(["account", "rename", "1", "renamed_label"])
    assert res.returncode == 0
    assert "Renamed account acc1@example.com to 'renamed_label'" in res.stdout
    
    # remove without --yes fails
    res = run_agy(["account", "remove", "1"])
    assert res.returncode == 1
    assert "Error: Account removal requires --yes" in res.stderr
    
    # remove with --yes
    res = run_agy(["account", "remove", "1", "--yes"])
    assert res.returncode == 0
    assert "Removed account" in res.stdout

def test_agy_account_edge_cases(setup_test_env):
    test_dir = setup_test_env
    setup_standard_accounts(test_dir)
    
    # Out-of-bound use
    res = run_agy(["account", "use", "99"])
    assert res.returncode == 1
    assert "Error: Index 99 out of range" in res.stderr
    
    # Ambiguous select
    accounts = [
        {"email": "test-first@example.com", "token": {"refresh_token": "rt1"}},
        {"email": "test-second@example.com", "token": {"refresh_token": "rt2"}}
    ]
    write_accounts_json(test_dir, accounts)
    res = run_agy(["account", "use", "test"])
    assert res.returncode == 1
    assert "Error: Multiple accounts match 'test'" in res.stderr

def test_agy_account_add_update(setup_test_env):
    test_dir = setup_test_env
    setup_standard_accounts(test_dir)
    
    # Write a new active token file with same username
    new_token = {
        "email": "acc1@example.com",
        "auth_method": "consumer",
        "token": {"refresh_token": "rt_new_token"}
    }
    write_token_json(test_dir, new_token)
    
    # Add account (should update existing RT)
    res = run_agy(["account", "add"])
    assert res.returncode == 0
    
    # Verify accounts.json updated
    json_path = os.path.join(test_dir, "accounts.json")
    with open(json_path, "r") as f:
        updated = json.load(f)
    assert updated[0]["token"]["refresh_token"] == "rt_new_token"

# Feature 3: agy doctor
def test_agy_doctor(setup_test_env):
    test_dir = setup_test_env
    setup_standard_accounts(test_dir)
    
    res = run_agy(["doctor"])
    assert res.returncode == 0
    assert "AGY account health: OK" in res.stdout
    
    # Missing files report
    os.remove(os.path.join(test_dir, "antigravity-oauth-token"))
    res = run_agy(["doctor"])
    assert res.returncode == 0
    assert "active token file is missing" in res.stdout
    
    # Non-array config
    with open(os.path.join(test_dir, "accounts.json"), "w") as f:
        json.dump({"not": "an array"}, f)
    res = run_agy(["doctor", "--json"])
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["ok"] is False

# Feature 4: agy backup/restore
def test_agy_backup_restore(setup_test_env):
    test_dir = setup_test_env
    setup_standard_accounts(test_dir)
    
    # Backup
    res = run_agy(["backup"])
    assert res.returncode == 0
    assert "Backup created" in res.stdout
    
    # Custom path
    custom_path = os.path.join(test_dir, "my-custom-backup.json")
    res = run_agy(["backup", "--out", custom_path])
    assert res.returncode == 0
    assert os.path.exists(custom_path)
    
    # Modify current accounts
    accounts = [{"email": "hacked@example.com", "token": {"refresh_token": "rt3"}}]
    write_accounts_json(test_dir, accounts)
    
    # Restore specific path without --yes fails
    res = run_agy(["restore", custom_path])
    assert res.returncode == 1
    assert "Error: Restore requires --yes" in res.stderr
    
    # Restore specific path with --yes
    res = run_agy(["restore", custom_path, "--yes"])
    assert res.returncode == 0
    assert "Accounts restored" in res.stdout
    
    # Verify main accounts.json restored
    with open(os.path.join(test_dir, "accounts.json"), "r") as f:
        restored = json.load(f)
    assert restored[0]["email"] == "acc1@example.com"

# Feature 5: agy weekly
def test_agy_weekly(setup_test_env):
    test_dir = setup_test_env
    setup_standard_accounts(test_dir)
    
    # Write mock logs
    log_dir = os.path.join(test_dir, "log")
    os.makedirs(log_dir, exist_ok=True)
    
    # Log 1: acc1 usage (Gemini)
    log_path1 = os.path.join(log_dir, "cli-1.log")
    with open(log_path1, "w") as f:
        f.write('applyAuthResult: email=acc1@example.com\n')
        f.write('label="Gemini 3.5 Flash (High)"\n')
        f.write('HandleUserInput called with text: User prompt 1\n')
        f.write('HandleUserInput called with text: User prompt 2\n')
        
    # Log 2: acc2 usage (Opus)
    log_path2 = os.path.join(log_dir, "cli-2.log")
    with open(log_path2, "w") as f:
        f.write('applyAuthResult: email=acc2@example.com\n')
        f.write('label="Claude Opus 4.6 (Thinking)"\n')
        f.write('HandleUserInput called with text: User prompt 3\n')
        
    res = run_agy(["weekly"])
    assert res.returncode == 0
    assert "acc1" in res.stdout
    assert "acc2" in res.stdout
    assert "2 " in res.stdout  # session prompts count for acc1
    assert "1 " in res.stdout  # session prompts count for acc2

def test_agy_weekly_old_logs(setup_test_env):
    test_dir = setup_test_env
    setup_standard_accounts(test_dir)
    
    log_dir = os.path.join(test_dir, "log")
    os.makedirs(log_dir, exist_ok=True)
    
    log_path = os.path.join(log_dir, "cli-old.log")
    with open(log_path, "w") as f:
        f.write('applyAuthResult: email=acc1@example.com\n')
        f.write('label="Gemini 3.5 Flash (High)"\n')
        f.write('HandleUserInput called with text: User prompt\n')
        
    # set modification time to 10 days ago
    old_time = time.time() - (10 * 24 * 3600)
    os.utime(log_path, (old_time, old_time))
    
    res = run_agy(["weekly"])
    assert res.returncode == 0
    assert "User prompt" not in res.stdout

# Feature 6: Legacy Compatibility Commands
def test_agy_legacy_compatibility(setup_test_env):
    test_dir = setup_test_env
    setup_standard_accounts(test_dir)
    
    # ls -> account list
    res = run_agy(["ls"])
    assert res.returncode == 0
    assert "acc1@example.com" in res.stdout
    
    # current -> account current
    res = run_agy(["current"])
    assert res.returncode == 0
    assert "acc1@example.com" in res.stdout
    
    # select -> account use
    res = run_agy(["select", "2"])
    assert res.returncode == 0
    assert "Switched active account to acc2" in res.stdout
    
    # Uppercase command input
    res = run_agy(["help", "account"])
    assert res.returncode == 0
    assert "usage: agy account" in res.stdout
    
    # Typo suggestions
    res = run_agy(["_suggest", "stat"])
    assert res.returncode == 2
    assert "Did you mean:" in res.stderr
    assert "agy status" in res.stderr

# Feature 7: Background Daemon Monitoring (agy auto)
def test_agy_auto_daemon(setup_test_env):
    test_dir = setup_test_env
    setup_standard_accounts(test_dir)
    
    # Run daemon loop with 1s interval as a subprocess
    cmd = [sys.executable, "tools/agy/agy-status.py", "auto", "--interval", "1"]
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=os.setsid
    )
    
    # Wait for daemon to print startup message
    time.sleep(1.0)
    
    # Terminate process with SIGINT
    os.killpg(os.getpgid(p.pid), signal.SIGINT)
    stdout, stderr = p.communicate(timeout=2)
    
    assert "Auto-rotate daemon is running" in stdout
    assert "Daemon stopped." in stdout

# Feature 8: Quota Rollover & Auto-Switching
def test_agy_auto_switch_highest_quota(setup_test_env):
    test_dir = setup_test_env
    # acc1 low quota (20%), acc2 high quota (90%), acc3 medium (50%)
    accounts = [
        {
            "email": "acc1@example.com",
            "token": {"refresh_token": "rt1"},
            "quota": "20%",
            "status": "🟢 Ready"
        },
        {
            "email": "acc2@example.com",
            "token": {"refresh_token": "rt2"},
            "quota": "90%",
            "status": "🟢 Ready"
        },
        {
            "email": "acc3@example.com",
            "token": {"refresh_token": "rt3"},
            "quota": "50%",
            "status": "🟢 Ready"
        }
    ]
    write_accounts_json(test_dir, accounts)
    write_token_json(test_dir, accounts[0]) # acc1 active
    
    # Run auto-switch (executed when current account has low quota)
    res = run_agy(["auto-switch"])
    assert res.returncode == 0
    assert "Auto-switched account to: acc2@example.com" in res.stdout
    assert "Quota: 90%" in res.stdout

def test_agy_transcript_parsing_progress_md(setup_test_env):
    test_dir = setup_test_env
    setup_standard_accounts(test_dir)
    
    # Set up mock log indicating Gemini quota error
    log_dir = os.path.join(test_dir, "log")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "cli-recent.log")
    with open(log_path, "w") as f:
        f.write('label="Gemini 3.5 Flash (High)"\n')
        f.write('RESOURCE_EXHAUSTED (code 429): Individual quota reached. Resets in 2h.\n')
    
    # Create mock brain session transcript
    brain_dir = os.path.join(test_dir, ".gemini/antigravity-cli/brain")
    os.makedirs(brain_dir, exist_ok=True)
    
    session_dir = os.path.join(brain_dir, "session-1")
    os.makedirs(session_dir, exist_ok=True)
    
    logs_dir = os.path.join(session_dir, ".system_generated/logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    transcript_path = os.path.join(logs_dir, "transcript.jsonl")
    with open(transcript_path, "w") as f:
        f.write(json.dumps({"type": "USER_INPUT", "content": "<USER_REQUEST>How to use agy?</USER_REQUEST>"}) + "\n")
        f.write(json.dumps({"type": "PLANNER_RESPONSE", "content": "You run agy status."}) + "\n")
        
    # Trigger auto-switch to run rollover generation via post-check
    # Make current account blocked to trigger auto-switch sequence
    accounts = load_accounts_from_file(test_dir)
    accounts[0]["quota"] = "20%" # triggers switch
    write_accounts_json(test_dir, accounts)
    
    res = run_agy(["post-check"])
    assert res.returncode == 0
    
    # Check .agy_progress.md was generated
    assert os.path.exists(".agy_progress.md")
    with open(".agy_progress.md", "r") as f:
        content = f.read()
    assert "User: How to use agy?" in content
    assert "Assistant: You run agy status." in content
    
    # Clean up local file
    try:
        os.remove(".agy_progress.md")
    except OSError:
        pass

# Helper to load accounts in test
def load_accounts_from_file(test_dir):
    json_path = os.path.join(test_dir, "accounts.json")
    with open(json_path, "r") as f:
        return json.load(f)

# Feature 9: Safe Default Blocks & Expirations
def test_agy_block_expiration(setup_test_env):
    test_dir = setup_test_env
    setup_standard_accounts(test_dir)
    
    # Block account, but with blocked_until timestamp in the PAST (expired)
    past_time = (datetime.now() - timedelta(minutes=5)).isoformat()
    accounts = load_accounts_from_file(test_dir)
    accounts[0]["status"] = "🔴 Blocked"
    accounts[0]["blocked_until"] = past_time
    write_accounts_json(test_dir, accounts)
    
    # Trigger auto-switch; since block is expired, it assumes Ready and doesn't switch
    res = run_agy(["auto-switch"])
    assert res.returncode == 0
    assert "SWITCH_ACCOUNT" not in res.stdout
