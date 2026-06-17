import unittest
from pathlib import Path
import os
import sys

# Add server_hub to path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server_hub.handler import is_safe_path

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
from server_hub.mcp_manager import save_mcp_configs

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
