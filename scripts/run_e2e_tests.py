#!/usr/bin/env python3
import subprocess
import time
import sys
import urllib.request
import urllib.error
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent

def wait_for_port(port: int, timeout: float = 10.0) -> bool:
    start_time = time.time()
    url = f"http://127.0.0.1:{port}"
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as conn:
                if conn.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionRefusedError, Exception):
            pass
        time.sleep(0.5)
    return False

def run_node_script(script_name: str) -> bool:
    print(f"\n🚀 Running E2E Test: {script_name}...")
    script_path = REPO_DIR / "frontend" / script_name
    
    # We must run E2E scripts inside frontend dir or using node
    res = subprocess.run(["node", str(script_path)], cwd=str(REPO_DIR))
    if res.returncode == 0:
        print(f"✅ {script_name} PASSED")
        return True
    else:
        print(f"❌ {script_name} FAILED (Exit Code: {res.returncode})")
        return False

def main() -> None:
    # 1. Start servers
    print("Starting background dashboard servers on ports 8000 and 8555...")
    server_8000 = subprocess.Popen(
        [sys.executable, "server.py", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(REPO_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    server_8555 = subprocess.Popen(
        [sys.executable, "server.py", "--host", "127.0.0.1", "--port", "8555"],
        cwd=str(REPO_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    all_passed = True
    try:
        # 2. Wait for servers to be active
        print("Waiting for servers to become responsive...")
        if not wait_for_port(8000):
            print("❌ Timeout waiting for server on port 8000")
            all_passed = False
            return
            
        if not wait_for_port(8555):
            print("❌ Timeout waiting for server on port 8555")
            all_passed = False
            return

        print("🟢 Servers are responsive! Initiating tests...")

        # 3. Run E2E Test Scripts
        tests = [
            "verify-layout.cjs",
            "test-e2e.cjs",
            "test-apply-scenarios.cjs",
            "test-analytics-e2e.cjs"
        ]

        for test in tests:
            if not run_node_script(test):
                all_passed = False
                # Continue running other tests to get full feedback
                
    finally:
        # 4. Clean up background servers
        print("\nStopping background servers...")
        server_8000.terminate()
        server_8555.terminate()
        try:
            server_8000.wait(timeout=2.0)
            server_8555.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            server_8000.kill()
            server_8555.kill()
        print("🟢 Cleaned up background processes.")

    if not all_passed:
        print("\n❌ E2E Integration Suite: FAILED")
        sys.exit(1)
    else:
        print("\n🎉 E2E Integration Suite: ALL PASSED")
        sys.exit(0)

if __name__ == "__main__":
    main()
