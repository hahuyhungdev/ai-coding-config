import sys
import unittest
from pathlib import Path
from unittest.mock import patch


AGY_TOOLS = Path(__file__).resolve().parents[1] / "tools" / "agy"
if str(AGY_TOOLS) not in sys.path:
    sys.path.insert(0, str(AGY_TOOLS))


class TestPtyClient(unittest.TestCase):
    def test_windows_native_keyring_is_cleared_after_account_switch(self):
        import utils

        with patch.object(utils.os, "name", "nt"), patch.object(utils.subprocess, "run") as run:
            utils.clear_windows_native_keyring()

        run.assert_called_once_with(
            ["cmdkey.exe", "/delete:gemini:antigravity"],
            stdout=utils.subprocess.DEVNULL,
            stderr=utils.subprocess.DEVNULL,
            check=False,
        )

    def test_windows_uses_windows_pty_backend(self):
        import pty_client

        with patch.object(pty_client.sys, "platform", "win32"), patch.object(
            pty_client, "_get_quota_via_windows_pty", return_value="quota output"
        ) as windows_backend:
            result = pty_client.get_quota_via_pty("account@example.com", sandbox_dir="C:\\sandbox")

        self.assertEqual(result, "quota output")
        windows_backend.assert_called_once_with("account@example.com", sandbox_dir="C:\\sandbox")


if __name__ == "__main__":
    unittest.main()
