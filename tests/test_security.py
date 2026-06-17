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
