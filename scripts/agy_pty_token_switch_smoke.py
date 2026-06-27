#!/usr/bin/env python3
"""PTY smoke test for agy token switching during a live session.

This test uses a temporary HOME and a fake agy-bin. It verifies that the
auto-rotate daemon can switch the active token while a terminal session is
still running. The fake session deliberately re-reads the token file so the
test can observe whether the changed token is visible to a live process.
"""

import json
import os
import pty
import select
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parent.parent
TOOLS_AGY_DIR = REPO_DIR / "tools" / "agy"


FAKE_AGY_BIN = r'''#!/usr/bin/env python3
import json
import os
import select
import sys
import time
from pathlib import Path


TOKEN_PATH = Path.home() / ".gemini" / "antigravity-cli" / "antigravity-oauth-token"


def token_data():
    try:
        return json.loads(TOKEN_PATH.read_text())
    except Exception:
        return {}


def account_name():
    data = token_data()
    return data.get("email") or data.get("name") or "unknown"


def refresh_token():
    return token_data().get("token", {}).get("refresh_token", "missing")


def quota_screen(email):
    if email.startswith("low"):
        five_hour = 25
        weekly = 90
    elif email.startswith("next"):
        five_hour = 80
        weekly = 80
    else:
        five_hour = 95
        weekly = 95
    return f"""
GEMINI MODELS
  Weekly Limit
    [fake] {weekly}.00%
    {weekly}% remaining · Refreshes in 99h 00m
  Five Hour Limit
    [fake] {five_hour}.00%
    {five_hour}% remaining · Refreshes in 4h 00m

CLAUDE AND GPT MODELS
  Weekly Limit
    [fake] 100.00%
    Quota available
  Five Hour Limit
    [fake] 100.00%
    Quota available
"""


print("FAKE_AGY_BIN_START", flush=True)
print(">", flush=True)
deadline = time.time() + 8
last_print = 0

while time.time() < deadline:
    now = time.time()
    if now - last_print >= 0.5:
        print(f"SESSION_TOKEN:{refresh_token()}:{account_name()}", flush=True)
        last_print = now

    ready, _, _ = select.select([sys.stdin], [], [], 0.1)
    if not ready:
        continue
    line = sys.stdin.readline()
    if not line:
        break
    command = line.strip()
    if command == "/usage":
        print(quota_screen(account_name()), flush=True)
        print(">", flush=True)
    elif command == "/exit":
        break

print("FAKE_AGY_BIN_EXIT", flush=True)
'''


def write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def copy_runtime(home: Path) -> tuple[Path, Path]:
    agy_dir = home / ".gemini" / "antigravity-cli"
    bin_dir = home / ".local" / "bin"
    agy_dir.mkdir(parents=True)
    bin_dir.mkdir(parents=True)

    for source in TOOLS_AGY_DIR.iterdir():
        if source.is_file() and (source.suffix == ".py" or source.name == "README.md"):
            shutil.copy2(source, agy_dir / source.name)

    shutil.copy2(TOOLS_AGY_DIR / "agy", bin_dir / "agy")
    (bin_dir / "agy").chmod(0o755)
    write_executable(bin_dir / "agy-bin", FAKE_AGY_BIN)
    return agy_dir, bin_dir


def seed_accounts(agy_dir: Path) -> None:
    accounts = [
        {
            "email": "low@example.com",
            "token": {"refresh_token": "rt-low"},
            "status": "🟢 Ready",
            "quota": "5H:25%/W:90%",
            "reset_info": "",
            "model_quotas": {},
        },
        {
            "email": "next@example.com",
            "token": {"refresh_token": "rt-next"},
            "status": "🟢 Ready",
            "quota": "5H:80%/W:80%",
            "reset_info": "",
            "model_quotas": {},
        },
        {
            "email": "high@example.com",
            "token": {"refresh_token": "rt-high"},
            "status": "🟢 Ready",
            "quota": "5H:95%/W:95%",
            "reset_info": "",
            "model_quotas": {},
        },
    ]
    (agy_dir / "accounts.json").write_text(json.dumps(accounts, indent=2))
    (agy_dir / "antigravity-oauth-token").write_text(json.dumps(accounts[0], indent=2))
    (agy_dir / "settings.json").write_text(json.dumps({"rotationPolicy": "highest-quota"}, indent=2))


def start_pty_session(home: Path, bin_dir: Path) -> tuple[subprocess.Popen, int]:
    master, slave = pty.openpty()
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    process = subprocess.Popen(
        [str(bin_dir / "agy-bin")],
        cwd=str(REPO_DIR),
        env=env,
        stdin=slave,
        stdout=slave,
        stderr=slave,
        text=False,
        start_new_session=True,
    )
    os.close(slave)
    return process, master


def read_available(master: int, timeout: float) -> str:
    output = bytearray()
    deadline = time.time() + timeout
    while time.time() < deadline:
        ready, _, _ = select.select([master], [], [], 0.1)
        if not ready:
            continue
        try:
            chunk = os.read(master, 4096)
        except OSError:
            break
        if not chunk:
            break
        output.extend(chunk)
    return output.decode(errors="ignore")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="agy-pty-token-switch-") as tmp:
        home = Path(tmp) / "home"
        agy_dir, bin_dir = copy_runtime(home)
        seed_accounts(agy_dir)

        session, master = start_pty_session(home, bin_dir)

        env = os.environ.copy()
        env["HOME"] = str(home)
        env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
        daemon = subprocess.Popen(
            [sys.executable, str(agy_dir / "auto_rotate_daemon.py"), "--interval", "1"],
            cwd=str(REPO_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        try:
            session_output = read_available(master, timeout=10)
        finally:
            if session.poll() is None:
                try:
                    os.killpg(session.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            if daemon.poll() is None:
                daemon.send_signal(signal.SIGINT)
            daemon_output, _ = daemon.communicate(timeout=5)
            os.close(master)

        active = json.loads((agy_dir / "antigravity-oauth-token").read_text())
        active_token = active.get("token", {}).get("refresh_token")
        saw_initial = "SESSION_TOKEN:rt-low:low@example.com" in session_output
        saw_switched = "SESSION_TOKEN:rt-high:high@example.com" in session_output

        print("Smoke test: PTY token switch during live fake session")
        print(f"tmp_home: {home}")
        print(f"active_token_after_daemon: {active_token}")
        print(f"saw_initial_token_in_session: {saw_initial}")
        print(f"saw_switched_token_in_session: {saw_switched}")
        print("")
        print("daemon_output:")
        print(daemon_output.strip())
        print("")
        print("session_output:")
        print(session_output.strip())

        if active_token != "rt-high":
            print("FAIL: daemon did not switch active token to the highest quota account", file=sys.stderr)
            return 2
        if not saw_initial or not saw_switched:
            print("FAIL: live session did not observe both initial and switched token", file=sys.stderr)
            return 3
        print("PASS: daemon switched token while PTY session was still running")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
