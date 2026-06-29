import unittest
from pathlib import Path
import os
import sys

# Add backend to path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.handler import is_safe_path

class TestSecurityPathValidation(unittest.TestCase):
    def test_is_safe_path_validates_correctly(self):
        allowed_bases = [
            Path("/tmp/allowed1"),
            Path("/tmp/allowed2")
        ]
        
        # Test exact match
        self.assertTrue(is_safe_path("/tmp/allowed1", allowed_bases))
        
        # Test subpaths
        self.assertTrue(is_safe_path("/tmp/allowed1/sub/file.txt", allowed_bases))
        self.assertTrue(is_safe_path("/tmp/allowed2/another.png", allowed_bases))
        
        # Test relative traversal to safe subpaths
        self.assertTrue(is_safe_path("/tmp/allowed1/sub/../file.txt", allowed_bases))
        
        # Test directory traversal attacks
        self.assertFalse(is_safe_path("/tmp/allowed1/../unsafe/file.txt", allowed_bases))
        self.assertFalse(is_safe_path("/etc/passwd", allowed_bases))
        self.assertFalse(is_safe_path("/tmp/unsafe", allowed_bases))
        
        # Test non-existent paths (should still resolve relative path components)
        self.assertFalse(is_safe_path("/tmp/allowed1/../allowed3/file.txt", allowed_bases))

from unittest.mock import patch
import tempfile
from backend.mcp_manager import save_mcp_configs

class TestMCPPermissions(unittest.TestCase):
    def test_mcp_configs_have_strict_permissions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_home = Path(tmpdir)
            
            # Setup Codex config to exist so it gets processed
            codex_dir = tmp_home / ".codex"
            codex_dir.mkdir()
            codex_toml = codex_dir / "config.toml"
            codex_toml.write_text("[mcp_servers]\n")
            
            # Mock Path.home() to return tmp_home
            with patch("pathlib.Path.home", return_value=tmp_home):
                save_mcp_configs({"playwright": {"type": "stdio", "command": "npx"}}, [])
                
            # Verify the files exist and have correct permissions
            claude_json = tmp_home / ".claude.json"
            gemini_json = tmp_home / ".gemini" / "config" / "mcp_config.json"
            
            self.assertTrue(claude_json.exists())
            self.assertTrue(gemini_json.exists())
            self.assertTrue(codex_toml.exists())
            
            if os.name == 'posix':
                self.assertEqual(os.stat(claude_json).st_mode & 0o777, 0o600)
                self.assertEqual(os.stat(gemini_json).st_mode & 0o777, 0o600)
                self.assertEqual(os.stat(codex_toml).st_mode & 0o777, 0o600)

import threading
import json
import urllib.request
import urllib.error

class TestSimulatorExecuteSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Import app
        from server import app
        import uvicorn
        import socket
        import time
        import threading
        
        # We set a test session token
        cls.token = "test-security-token-123456"
        app.state.session_token = cls.token
        
        # Find a free port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        cls.port = s.getsockname()[1]
        s.close()
        
        # Start server using uvicorn
        config = uvicorn.Config(app, host="127.0.0.1", port=cls.port, log_level="error")
        cls.server = uvicorn.Server(config)
        cls.server_thread = threading.Thread(target=cls.server.run)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.server_thread.join()

    def test_execute_fails_without_token(self):
        url = f"http://127.0.0.1:{self.port}/api/simulator/execute"
        payload = {"action": "run_command", "args": {"CommandLine": "echo hello"}}
        data = json.dumps(payload).encode("utf-8")
        
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Origin": "http://127.0.0.1"
            }
        )
        
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req)
        self.assertEqual(cm.exception.code, 401)

    def test_execute_succeeds_with_header_token(self):
        url = f"http://127.0.0.1:{self.port}/api/simulator/execute"
        payload = {"action": "run_command", "args": {"CommandLine": "echo hello"}}
        data = json.dumps(payload).encode("utf-8")
        
        # Test X-Session-Token
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-Session-Token": self.token,
                "Origin": "http://127.0.0.1"
            }
        )
        response = urllib.request.urlopen(req)
        self.assertEqual(response.status, 200)
        res_data = json.loads(response.read().decode("utf-8"))
        self.assertEqual(res_data.get("status"), "success")

    def test_execute_succeeds_with_cookie_token(self):
        url = f"http://127.0.0.1:{self.port}/api/simulator/execute"
        payload = {"action": "run_command", "args": {"CommandLine": "echo hello"}}
        data = json.dumps(payload).encode("utf-8")
        
        # Test Cookie header
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Cookie": f"session_token={self.token}",
                "Origin": "http://127.0.0.1"
            }
        )
        response = urllib.request.urlopen(req)
        self.assertEqual(response.status, 200)
        res_data = json.loads(response.read().decode("utf-8"))
        self.assertEqual(res_data.get("status"), "success")

    def test_execute_denies_command_injection(self):
        url = f"http://127.0.0.1:{self.port}/api/simulator/execute"
        payload = {"action": "run_command", "args": {"CommandLine": "echo hello; rm -rf /"}}
        data = json.dumps(payload).encode("utf-8")
        
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-Session-Token": self.token,
                "Origin": "http://127.0.0.1"
            }
        )
        response = urllib.request.urlopen(req)
        self.assertEqual(response.status, 200)
        res_data = json.loads(response.read().decode("utf-8"))
        self.assertEqual(res_data.get("status"), "error")
        self.assertIn("Access denied", res_data.get("message", ""))

    def test_execute_denies_path_traversal(self):
        url = f"http://127.0.0.1:{self.port}/api/simulator/execute"
        payload = {"action": "view_file", "args": {"AbsolutePath": "/etc/passwd"}}
        data = json.dumps(payload).encode("utf-8")
        
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-Session-Token": self.token,
                "Origin": "http://127.0.0.1"
            }
        )
        response = urllib.request.urlopen(req)
        self.assertEqual(response.status, 200)
        res_data = json.loads(response.read().decode("utf-8"))
        self.assertEqual(res_data.get("status"), "error")
        self.assertIn("Access denied", res_data.get("message", ""))

    def test_execute_allows_placeholder_view_file(self):
        url = f"http://127.0.0.1:{self.port}/api/simulator/execute"
        payload = {"action": "view_file", "args": {"AbsolutePath": "/absolute/path/to/project/server.py"}}
        data = json.dumps(payload).encode("utf-8")
        
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-Session-Token": self.token,
                "Origin": "http://127.0.0.1"
            }
        )
        response = urllib.request.urlopen(req)
        self.assertEqual(response.status, 200)
        res_data = json.loads(response.read().decode("utf-8"))
        self.assertEqual(res_data.get("status"), "success")
        self.assertIn("ConfigHandler", res_data.get("output", ""))
