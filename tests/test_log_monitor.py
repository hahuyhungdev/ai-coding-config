import os
import sys
import tempfile
import unittest
from pathlib import Path


tools_dir = Path(__file__).resolve().parent.parent / "tools" / "agy"
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

import log_monitor


class TestLogMonitor(unittest.TestCase):
    def test_get_newest_log_file_filters_by_min_mtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            old_log = log_dir / "cli-old.log"
            new_log = log_dir / "cli-new.log"
            ignored = log_dir / "not-cli.log"

            old_log.write_text("old", encoding="utf-8")
            new_log.write_text("new", encoding="utf-8")
            ignored.write_text("ignored", encoding="utf-8")

            os.utime(old_log, (100, 100))
            os.utime(new_log, (200, 200))
            os.utime(ignored, (300, 300))

            original_log_dir = log_monitor.LOG_DIR
            log_monitor.LOG_DIR = str(log_dir)
            try:
                self.assertEqual(log_monitor.get_newest_log_file(), str(new_log))
                self.assertEqual(log_monitor.get_newest_log_file(min_mtime=150), str(new_log))
                self.assertIsNone(log_monitor.get_newest_log_file(min_mtime=250))
            finally:
                log_monitor.LOG_DIR = original_log_dir


if __name__ == "__main__":
    unittest.main()
