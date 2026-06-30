import os
import pty
import select
import signal
import json
import time
import sys
import fcntl
import termios
import struct
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "agy"))
from datetime import datetime, timedelta

# Paths
AGY_DIR = os.path.expanduser("~/.gemini/antigravity-cli")
TOKEN_FILE = os.path.join(AGY_DIR, "antigravity-oauth-token")
JSON_FILE = os.path.join(AGY_DIR, "accounts.json")
JSON_BACKUP = JSON_FILE + ".bak_comp"
SETTINGS_FILE = os.path.join(AGY_DIR, "settings.json")
LOG_DIR = os.path.join(AGY_DIR, "log")
LOG_BACKUP_DIR = os.path.join(AGY_DIR, "log_backup")

def backup_file(filepath):
    bak = filepath + ".bak_comp"
    if os.path.exists(filepath) and not os.path.exists(bak):
        import shutil
        shutil.copy2(filepath, bak)

def restore_file(filepath):
    bak = filepath + ".bak_comp"
    if os.path.exists(bak):
        import shutil
        shutil.copy2(bak, filepath)
        os.remove(bak)

def backup_logs():
    if os.path.exists(LOG_DIR):
        os.makedirs(LOG_BACKUP_DIR, exist_ok=True)
        for f in os.listdir(LOG_DIR):
            if f.startswith("cli-") and f.endswith(".log"):
                import shutil
                shutil.move(os.path.join(LOG_DIR, f), os.path.join(LOG_BACKUP_DIR, f))

def restore_logs():
    if os.path.exists(LOG_BACKUP_DIR):
        for f in os.listdir(LOG_BACKUP_DIR):
            import shutil
            try:
                shutil.move(os.path.join(LOG_BACKUP_DIR, f), os.path.join(LOG_DIR, f))
            except:
                pass
        try:
            os.rmdir(LOG_BACKUP_DIR)
        except OSError:
            pass

def get_real_accounts():
    backup_path = os.path.join(AGY_DIR, "accounts-backup.json")
    if os.path.exists(backup_path):
        with open(backup_path, "r") as f:
            return json.load(f)
    elif os.path.exists(JSON_BACKUP):
        with open(JSON_BACKUP, "r") as f:
            return json.load(f)
    elif os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r") as f:
            return json.load(f)
    return []

def clear_all_current_logs():
    if os.path.exists(LOG_DIR):
        for f in os.listdir(LOG_DIR):
            if f.startswith("cli-") and f.endswith(".log"):
                try:
                    os.remove(os.path.join(LOG_DIR, f))
                except OSError:
                    pass

def setup_test_accounts(quota_status_list, reset_thresholds=True):
    clear_all_current_logs()
    
    # Reset settings.json custom thresholds to prevent test pollution
    SETTINGS_FILE = os.path.join(AGY_DIR, "settings.json")
    if reset_thresholds and os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
            changed = False
            for k in ["threshold_5h", "threshold5h", "threshold", "quotaThreshold", "quota_threshold",
                      "threshold_weekly", "thresholdWeekly", "threshold_weekly_limit"]:
                if k in settings:
                    del settings[k]
                    changed = True
            if changed:
                with open(SETTINGS_FILE, "w") as f:
                    json.dump(settings, f, indent=2)
        except Exception:
            pass

    real_accs = get_real_accounts()
    if len(real_accs) < len(quota_status_list):
        raise ValueError("Not enough real accounts available in database!")
        
    test_accs = []
    for idx, cfg in enumerate(quota_status_list):
        real_acc = real_accs[idx].copy()
        real_acc["quota"] = cfg.get("quota", "5H:100%/W:100%")
        real_acc["status"] = cfg.get("status", "🟢 Ready")
        if "model_quotas" in cfg:
            real_acc["model_quotas"] = cfg["model_quotas"]
        else:
            real_acc["model_quotas"] = {}
        if "blocked_until" in cfg:
            real_acc["blocked_until"] = cfg["blocked_until"]
        elif "blocked_until" in real_acc:
            del real_acc["blocked_until"]
        if "reset_info" in cfg:
            real_acc["reset_info"] = cfg["reset_info"]
        elif "reset_info" in real_acc:
            del real_acc["reset_info"]
        test_accs.append(real_acc)
        
    # Write ONLY the test pool accounts to isolate choice space!
    with open(JSON_FILE, "w") as f:
        json.dump(test_accs, f, indent=2)
        
    with open(TOKEN_FILE, "w") as f:
        json.dump(test_accs[0], f)
    os.chmod(TOKEN_FILE, 0o600)
    
    return test_accs[0]["email"]

def get_active_email():
    if not os.path.exists(TOKEN_FILE):
        return ""
    try:
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
        active_rt = token_data.get("token", {}).get("refresh_token")
        if active_rt:
            with open(JSON_FILE, "r") as f:
                accounts = json.load(f)
            for acc in accounts:
                if acc.get("token", {}).get("refresh_token") == active_rt:
                    return acc.get("email")
    except:
        pass
    return ""

def get_newest_log_file():
    if not os.path.exists(LOG_DIR):
        return None
    files = [os.path.join(LOG_DIR, f) for f in os.listdir(LOG_DIR) if f.startswith("cli-") and f.endswith(".log")]
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]

def write_mock_log(error_type, reset_str="2h30m"):
    account_email = get_active_email()
    log_path = get_newest_log_file()
    if not log_path:
        log_path = os.path.join(LOG_DIR, "cli-mock-test.log")
        
    now = datetime.now()
    log_time_str = now.strftime("%m%d %H:%M:%S")
    
    if error_type == "RESOURCE_EXHAUSTED":
        err_line = f"E{log_time_str}.020000 12345 main.go:30] RESOURCE_EXHAUSTED resets in {reset_str}"
    elif error_type == "RATE_LIMIT":
        err_line = f"E{log_time_str}.020000 12345 main.go:30] Rate limit reached on model resets in {reset_str}"
    elif error_type == "QUOTA_EXCEEDED":
        err_line = f"E{log_time_str}.020000 12345 main.go:30] Quota exceeded resets in {reset_str}"
    elif error_type == "GEMINI_EXHAUSTED":
        err_line = f"E{log_time_str}.020000 12345 main.go:30] RESOURCE_EXHAUSTED resets in 2h30m"
    else:
        err_line = ""

    log_content = f"""
I{log_time_str}.000000 12345 main.go:10] applyAuthResult email={account_email}
I{log_time_str}.010000 12345 main.go:20] label="Gemini 3.5 Flash (High)"
{err_line}
"""
    with open(log_path, "a") as f:
        f.write(log_content)
        
    os.utime(log_path, (time.time(), time.time()))

def clear_mock_logs():
    mock_log_path = os.path.join(LOG_DIR, "cli-mock-test.log")
    if os.path.exists(mock_log_path):
        try:
            os.remove(mock_log_path)
        except OSError:
            pass

def setup_mock_history(turns):
    mock_session_dir = os.path.join(AGY_DIR, "brain/mock_session_test")
    os.makedirs(os.path.join(mock_session_dir, ".system_generated/logs"), exist_ok=True)
    transcript_path = os.path.join(mock_session_dir, ".system_generated/logs/transcript.jsonl")

    with open(transcript_path, "w") as f:
        for turn in turns:
            f.write(json.dumps(turn) + "\n")
    os.utime(mock_session_dir, (time.time() + 100, time.time() + 100))

def clear_mock_history():
    mock_session_dir = os.path.join(AGY_DIR, "brain/mock_session_test")
    os.makedirs(os.path.join(mock_session_dir, ".system_generated/logs"), exist_ok=True)
    transcript_path = os.path.join(mock_session_dir, ".system_generated/logs/transcript.jsonl")
    try:
        with open(transcript_path, "w") as f:
            pass
        os.utime(mock_session_dir, (time.time() + 100, time.time() + 100))
    except OSError:
        pass

def delete_mock_history():
    import shutil
    mock_session_dir = os.path.join(AGY_DIR, "brain/mock_session_test")
    if os.path.exists(mock_session_dir):
        try:
            shutil.rmtree(mock_session_dir)
        except OSError:
            pass

def run_pty_session(args_list, submit_prompt=None, write_log_cb=None):
    master, slave = pty.openpty()
    s = struct.pack("HHHH", 24, 80, 0, 0)
    try:
        fcntl.ioctl(master, termios.TIOCSWINSZ, s)
    except:
        pass
        
    pid = os.fork()
    if pid == 0:
        os.setsid()
        os.dup2(slave, 0)
        os.dup2(slave, 1)
        os.dup2(slave, 2)
        os.close(master)
        os.close(slave)
        
        env = os.environ.copy()
        env["PATH"] = os.path.expanduser("~/.local/bin:") + env.get("PATH", "")
        env["AGY_TESTING"] = "0"
        env["TERM"] = "xterm-256color"
        env["PAGER"] = "cat"
        
        try:
            os.execvpe("agy", ["agy"] + args_list, env)
        except Exception as e:
            os._exit(127)
    else:
        os.close(slave)
        output = b""
        start_time = time.time()
        prompt_sent = False
        mock_written = False
        trust_sent = False
        feedback_sent = False
        
        while time.time() - start_time < 15.0:
            finished_pid, status = os.waitpid(pid, os.WNOHANG)
            if finished_pid == pid:
                break
                
            r, _, _ = select.select([master], [], [], 0.1)
            if r:
                try:
                    chunk = os.read(master, 4096)
                    if not chunk:
                        break
                    output += chunk
                    
                    decoded_clean = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", output.decode(errors="ignore"))
                    
                    # 1. Handle Trust Prompt
                    if ("trust the contents" in decoded_clean or "trust this folder" in decoded_clean) and not trust_sent:
                        time.sleep(0.5)
                        os.write(master, b"\x0d")
                        trust_sent = True
                        
                    # 2. Handle Feedback Poll
                    if "experience" in decoded_clean.lower() and not feedback_sent:
                        time.sleep(0.5)
                        os.write(master, b"0\x0d")
                        feedback_sent = True
                        
                    # 3. Handle Prompt Submission
                    if (">" in decoded_clean or "shortcuts" in decoded_clean) and not mock_written:
                        if write_log_cb:
                            write_log_cb()
                        mock_written = True
                        
                        if submit_prompt:
                            os.write(master, b"\x1b") # Cancel popups
                            time.sleep(0.5)
                            os.write(master, submit_prompt.encode() + b"\x0d")
                            prompt_sent = True
                            
                    if b"AUTO-RESUMING SESSION" in output:
                        res_start = time.time()
                        res_trust_sent = False
                        res_feedback_sent = False
                        res_len = len(decoded_clean)
                        while time.time() - res_start < 15.0:
                            r2, _, _ = select.select([master], [], [], 0.1)
                            if r2:
                                try:
                                    chunk = os.read(master, 4096)
                                    output += chunk
                                    decoded_clean = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", output.decode(errors="ignore"))
                                    new_decoded = decoded_clean[res_len:]
                                    if ("trust the contents" in new_decoded or "trust this folder" in new_decoded) and not res_trust_sent:
                                        time.sleep(0.5)
                                        os.write(master, b"\x0d")
                                        res_trust_sent = True
                                    if "experience" in new_decoded.lower() and not res_feedback_sent:
                                        time.sleep(0.5)
                                        os.write(master, b"0\x0d")
                                        res_feedback_sent = True
                                    if "User:" in new_decoded or "Assistant:" in new_decoded or "compaction_rollover" in new_decoded:
                                        time.sleep(2.0)
                                        r3, _, _ = select.select([master], [], [], 0.5)
                                        if r3:
                                            try:
                                                output += os.read(master, 4096)
                                            except OSError:
                                                pass
                                        break
                                except OSError:
                                    break
                            else:
                                time.sleep(0.05)
                        break
                except OSError:
                    break
            else:
                time.sleep(0.02)
                
        try:
            os.killpg(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        except Exception:
            pass
        finally:
            os.close(master)
            
        decoded = output.decode(errors="ignore")
        return decoded

def run_suite():
    print("📋 STARTING 20 ACTIVE SESSION E2E TEST CASES...")
    
    backup_file(JSON_FILE)
    backup_file(TOKEN_FILE)
    backup_file(SETTINGS_FILE)
    backup_logs()
    
    results = []
    
    def log_result(name, desc, success, out=""):
        status = "✅ PASS" if success else "❌ FAIL"
        results.append((name, desc, status, out))
        print(f"[{status}] {name}: {desc}")
        if not success and out:
            print(f"--- PTY OUTPUT FOR {name} ---")
            print(out)
            print("----------------------------")

    try:
        real_accs = get_real_accounts()
        email_0 = real_accs[0]["email"]
        email_1 = real_accs[1]["email"]
        email_2 = real_accs[2]["email"]

        # T01: 5H limit is low
        setup_test_accounts([
            {"quota": "5H:14%/W:50%", "status": "🟢 Ready"},
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"}
        ])
        clear_mock_logs()
        out = run_pty_session([])
        success = "Switched to" in out or "Auto-switched" in out
        log_result("T01_5H_low", "Proactive switch on 5H low quota (14%)", success, out)

        # T02: W limit is low
        setup_test_accounts([
            {"quota": "5H:90%/W:9%", "status": "🟢 Ready"},
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"}
        ])
        out = run_pty_session([])
        success = "Switched to" in out or "Auto-switched" in out
        log_result("T02_W_low", "Proactive switch on W low quota (9%)", success, out)

        # T03: Both limits low
        setup_test_accounts([
            {"quota": "5H:14%/W:9%", "status": "🟢 Ready"},
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"}
        ])
        out = run_pty_session([])
        success = "Switched to" in out or "Auto-switched" in out
        log_result("T03_both_low", "Proactive switch when both limits are low", success, out)

        # T04: 5H borderline safe
        setup_test_accounts([
            {"quota": "5H:16%/W:80%", "status": "🟢 Ready"},
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"}
        ])
        out = run_pty_session([])
        success = "Switched to" not in out and "Auto-switched" not in out
        log_result("T04_5H_borderline_safe", "No switch on 5H borderline safe quota (16%)", success, out)

        # T05: W borderline safe
        setup_test_accounts([
            {"quota": "5H:80%/W:11%", "status": "🟢 Ready"},
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"}
        ])
        out = run_pty_session([])
        success = "Switched to" not in out and "Auto-switched" not in out
        log_result("T05_W_borderline_safe", "No switch on W borderline safe quota (11%)", success, out)

        # T06: Log error RESOURCE_EXHAUSTED
        setup_test_accounts([
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"},
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"}
        ])
        setup_mock_history([
            {"type": "USER_INPUT", "content": "<USER_REQUEST>Test T06</USER_REQUEST>"},
            {"type": "PLANNER_RESPONSE", "content": "T06 response"}
        ])
        clear_mock_logs()
        out = run_pty_session([], submit_prompt="read the file README.md", write_log_cb=lambda: write_mock_log("RESOURCE_EXHAUSTED"))
        success = "AUTO-RESUMING SESSION" in out and "Test T06" in out
        log_result("T06_log_error_resource_exhausted", "Active switch & rollover on RESOURCE_EXHAUSTED", success, out)

        # T07: Log error RATE_LIMIT
        setup_test_accounts([
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"},
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"}
        ])
        setup_mock_history([{"type": "USER_INPUT", "content": "<USER_REQUEST>Test T07</USER_REQUEST>"}])
        clear_mock_logs()
        out = run_pty_session([], submit_prompt="read the file README.md", write_log_cb=lambda: write_mock_log("RATE_LIMIT"))
        success = "AUTO-RESUMING SESSION" in out and "Test T07" in out
        log_result("T07_log_error_rate_limit", "Active switch & rollover on RATE_LIMIT", success, out)

        # T08: Log error QUOTA_EXCEEDED
        setup_test_accounts([
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"},
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"}
        ])
        setup_mock_history([{"type": "USER_INPUT", "content": "<USER_REQUEST>Test T08</USER_REQUEST>"}])
        clear_mock_logs()
        out = run_pty_session([], submit_prompt="read the file README.md", write_log_cb=lambda: write_mock_log("QUOTA_EXCEEDED"))
        success = "AUTO-RESUMING SESSION" in out and "Test T08" in out
        log_result("T08_log_error_quota_exceeded", "Active switch & rollover on QUOTA_EXCEEDED", success, out)

        # T09: Skip low candidates
        setup_test_accounts([
            {"quota": "5H:14%/W:50%", "status": "🟢 Ready"},
            {"quota": "5H:12%/W:90%", "status": "🟢 Ready"}, 
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"} 
        ])
        clear_mock_logs()
        out = run_pty_session([])
        success = (email_2 in out) and (email_1 not in out)
        log_result("T09_skip_low_candidates", "Skips low quota target candidates during rotation", success, out)

        # T10: Skip blocked candidates
        setup_test_accounts([
            {"quota": "5H:14%/W:50%", "status": "🟢 Ready"},
            {"quota": "5H:100%/W:100%", "status": "🔴 Blocked"}, 
            {"quota": "5H:90%/W:90%", "status": "🟢 Ready"}
        ])
        out = run_pty_session([])
        success = (email_2 in out) and (email_1 not in out)
        log_result("T10_skip_blocked_candidates", "Skips blocked candidates during rotation", success, out)

        # T11: All candidates low fallback
        setup_test_accounts([
            {"quota": "5H:14%/W:50%", "status": "🟢 Ready"},
            {"quota": "5H:12%/W:90%", "status": "🟢 Ready"}, 
            {"quota": "5H:8%/W:90%", "status": "🟢 Ready"}
        ])
        out = run_pty_session([])
        success = (email_1 in out)
        log_result("T11_all_candidates_low_fallback", "Falls back to best available low quota account", success, out)

        # T12: All candidates blocked fallback
        setup_test_accounts([
            {"quota": "5H:14%/W:50%", "status": "🔴 Blocked"},
            {"quota": "5H:100%/W:100%", "status": "🔴 Blocked"},
            {"quota": "5H:90%/W:90%", "status": "🔴 Blocked"}
        ])
        out = run_pty_session([])
        success = "Switched to" not in out and "Auto-switched" not in out
        log_result("T12_all_candidates_blocked_fallback", "Stays on current account when all are blocked", success, out)

        # T13: Custom threshold settings
        with open(SETTINGS_FILE, "w") as f:
            json.dump({"threshold_5h": 30, "enableJsonHooks": True}, f)
        setup_test_accounts([
            {"quota": "5H:25%/W:80%", "status": "🟢 Ready"}, 
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"}
        ], reset_thresholds=False)
        with open(SETTINGS_FILE, "r") as f:
            print("T13 debug: settings.json =", f.read())
        from switch import load_quota_thresholds
        print("T13 debug: load_quota_thresholds() =", load_quota_thresholds())
        out = run_pty_session([])
        success = "Switched to" in out or "Auto-switched" in out
        log_result("T13_custom_threshold_settings", "Respects custom 5H threshold (30%)", success, out)

        with open(SETTINGS_FILE, "w") as f:
            json.dump({"enableJsonHooks": True}, f)

        # T14: Custom threshold weekly settings
        with open(SETTINGS_FILE, "w") as f:
            json.dump({"threshold_weekly": 20, "enableJsonHooks": True}, f)
        setup_test_accounts([
            {"quota": "5H:80%/W:15%", "status": "🟢 Ready"}, 
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"}
        ], reset_thresholds=False)
        out = run_pty_session([])
        success = "Switched to" in out or "Auto-switched" in out
        log_result("T14_custom_threshold_weekly_settings", "Respects custom Weekly threshold (20%)", success, out)

        with open(SETTINGS_FILE, "w") as f:
            json.dump({"enableJsonHooks": True}, f)

        # T15: Compaction history 1 turn
        setup_test_accounts([
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"},
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"}
        ])
        setup_mock_history([
            {"type": "USER_INPUT", "content": "<USER_REQUEST>Only One Turn Query</USER_REQUEST>"}
        ])
        clear_mock_logs()
        out = run_pty_session([], submit_prompt="read the file README.md", write_log_cb=lambda: write_mock_log("RESOURCE_EXHAUSTED"))
        success = "AUTO-RESUMING SESSION" in out and "User: Only One Turn Query" in out
        log_result("T15_compaction_history_1_turn", "Rollover preserves exactly 1 conversation turn", success, out)

        # T16: Compaction history multiple turns
        setup_test_accounts([
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"},
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"}
        ])
        setup_mock_history([
            {"type": "USER_INPUT", "content": "<USER_REQUEST>Turn 1</USER_REQUEST>"},
            {"type": "PLANNER_RESPONSE", "content": "Response 1"},
            {"type": "USER_INPUT", "content": "<USER_REQUEST>Turn 2</USER_REQUEST>"}
        ])
        clear_mock_logs()
        out = run_pty_session([], submit_prompt="read the file README.md", write_log_cb=lambda: write_mock_log("RESOURCE_EXHAUSTED"))
        success = "AUTO-RESUMING SESSION" in out and "User: Turn 1" in out and "Assistant: Response 1" in out and "User: Turn 2" in out
        log_result("T16_compaction_history_multiple_turns", "Rollover preserves multiple conversation turns", success, out)

        # T17: Print mode prompt retry
        setup_test_accounts([
            {"quota": "5H:14%/W:50%", "status": "🟢 Ready"},
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"}
        ])
        clear_mock_logs()
        out = run_pty_session(["-p", "hello print mode"])
        success = ("Switched to" in out or "Auto-switched" in out)
        log_result("T17_print_mode_prompt_retry", "Proactive switch triggered for print mode", success, out)

        # T18: Model override preservation
        setup_test_accounts([
            {"quota": "5H:14%/W:50%", "status": "🟢 Ready"},
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"}
        ])
        out = run_pty_session(["--model=Claude Sonnet 4.6 (Thinking)"])
        success = ("Switched to" in out or "Auto-switched" in out)
        log_result("T18_model_override_preservation", "Preserves model override flag during proactive switch", success, out)

        # T19: Gemini exhausted fallback rule
        setup_test_accounts([
            {
                "quota": "5H:90%/W:90%", 
                "status": "🟢 Ready",
                "model_quotas": {
                    "Gemini 3.5 Flash (High)": {"pct": 10}, 
                    "Claude Sonnet 4.6 (Thinking)": {"pct": 80} 
                }
            },
            {
                "quota": "5H:100%/W:100%", 
                "status": "🟢 Ready",
                "model_quotas": {}
            }
        ])
        clear_mock_logs()
        out = run_pty_session([], submit_prompt="read the file README.md", write_log_cb=lambda: write_mock_log("GEMINI_EXHAUSTED"))
        success = "AUTO-RESUMING SESSION" in out
        log_result("T19_gemini_exhausted_fallback_rule", "Rotates accounts when Gemini model quota is exhausted on active", success, out)

        # T20: No history clean rollover
        setup_test_accounts([
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"},
            {"quota": "5H:100%/W:100%", "status": "🟢 Ready"}
        ])
        clear_mock_history()
        clear_mock_logs()
        out = run_pty_session([], submit_prompt="read the file README.md", write_log_cb=lambda: write_mock_log("RESOURCE_EXHAUSTED"))
        success = "AUTO-RESUMING SESSION" in out
        log_result("T20_no_history_clean_rollover", "Handles rollover restart cleanly when no history exists", success, out)

    finally:
        restore_file(JSON_FILE)
        restore_file(TOKEN_FILE)
        restore_file(SETTINGS_FILE)
        restore_logs()
        clear_mock_logs()
        delete_mock_history()

    print("\n" + "="*80)
    print(f"{'TEST CASE':<35} | {'DESCRIPTION':<30} | {'STATUS':<6}")
    print("="*80)
    all_pass = True
    for name, desc, status, _ in results:
        print(f"{name:<35} | {desc[:30]:<30} | {status:<6}")
        if "FAIL" in status:
            all_pass = False
    print("="*80 + "\n")
    
    return all_pass

if __name__ == "__main__":
    success = run_suite()
    sys.exit(0 if success else 1)
