import os
import sys
import unittest
from importlib.machinery import SourceFileLoader
from unittest.mock import patch


tools_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../tools/agy"))
if tools_dir not in sys.path:
    sys.path.insert(0, tools_dir)

auto_rotate_daemon = SourceFileLoader(
    "auto_rotate_daemon", os.path.join(tools_dir, "auto_rotate_daemon.py")
).load_module()


class TestAutoRotateDaemon(unittest.TestCase):
    def test_run_check_refreshes_live_status_before_switching(self):
        calls = []

        with patch.object(auto_rotate_daemon, "get_account_status", side_effect=lambda: calls.append("refresh")), \
             patch.object(auto_rotate_daemon, "auto_switch_account", side_effect=lambda quiet=False: calls.append("switch")):
            auto_rotate_daemon.run_check(refresh_status=True)

        self.assertEqual(calls, ["refresh", "switch"])


if __name__ == "__main__":
    unittest.main()
