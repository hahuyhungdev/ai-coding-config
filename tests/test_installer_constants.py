import unittest
from pathlib import Path
from unittest import mock
import os

from installer.constants import get_real_home

class TestInstallerConstants(unittest.TestCase):
    @mock.patch("pathlib.Path.home")
    def test_get_real_home_normal(self, mock_home):
        # When home is normal, it should return that home
        mock_home.return_value = Path("/home/testuser")
        self.assertEqual(get_real_home(), Path("/home/testuser"))

    @mock.patch("pathlib.Path.home")
    @mock.patch("os.getcwd")
    def test_get_real_home_sandboxed_unix(self, mock_getcwd, mock_home):
        # When home is temporary/sandboxed
        mock_home.return_value = Path("/tmp/tmpjmlgqr99")
        # And CWD is not in tmp
        mock_getcwd.return_value = "/home/testuser/projects/personals/ai-coding-config"
        
        # get_real_home should extract the real home /home/testuser
        # We pass an explicit check_path list to avoid picking up this test file's actual path
        check_paths = ["/home/testuser/projects/personals/ai-coding-config/installer/constants.py"]
        self.assertEqual(get_real_home(check_paths=check_paths), Path("/home/testuser"))

    @mock.patch("pathlib.Path.home")
    @mock.patch("os.getcwd")
    def test_get_real_home_sandboxed_mac(self, mock_getcwd, mock_home):
        mock_home.return_value = Path("/var/folders/temp-sandbox")
        mock_getcwd.return_value = "/Users/testuser/projects/personals/ai-coding-config"
        
        check_paths = ["/Users/testuser/projects/personals/ai-coding-config/installer/constants.py"]
        self.assertEqual(get_real_home(check_paths=check_paths), Path("/Users/testuser"))

    @mock.patch("pathlib.Path.home")
    @mock.patch("os.getcwd")
    def test_get_real_home_sandboxed_windows(self, mock_getcwd, mock_home):
        mock_home.return_value = Path("C:\\Users\\testuser\\AppData\\Local\\Temp\\sandbox")
        mock_getcwd.return_value = "C:\\Users\\testuser\\projects\\ai-coding-config"
        
        check_paths = ["C:\\Users\\testuser\\projects\\ai-coding-config\\installer\\constants.py"]
        self.assertEqual(get_real_home(check_paths=check_paths), Path("C:\\Users\\testuser"))

    @mock.patch("pathlib.Path.home")
    @mock.patch("os.getcwd")
    def test_get_real_home_in_unit_test(self, mock_getcwd, mock_home):
        # In a unit test, both home and cwd are under tmp/
        mock_home.return_value = Path("/tmp/mock_home")
        mock_getcwd.return_value = "/tmp/mock_cwd"
        
        # It should respect the mock home and not override it
        self.assertEqual(get_real_home(), Path("/tmp/mock_home"))
