import os
import subprocess
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestAgyWrapper(unittest.TestCase):
    def test_interactive_exit_runs_post_check_and_resumes_on_switch(self):
        repo_root = Path(__file__).resolve().parents[1]
        wrapper = repo_root / "tools" / "agy" / "agy"

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            work = root / "work"
            agy_dir = root / "agy"
            bin_dir = home / ".local" / "bin"
            home.mkdir()
            work.mkdir()
            agy_dir.mkdir()
            bin_dir.mkdir(parents=True)

            agy_status = agy_dir / "agy-status.py"
            agy_status.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env python3
                    import pathlib
                    import sys

                    log = pathlib.Path({str(root / "status.log")!r})
                    command = sys.argv[1] if len(sys.argv) > 1 else ""
                    log.write_text(log.read_text() + command + "\\n" if log.exists() else command + "\\n")
                    if command == "post-check":
                        switched = pathlib.Path({str(root / "switched")!r})
                        if switched.exists():
                            sys.exit(1)
                        switched.touch()
                        pathlib.Path({str(agy_dir / ".active_conv_id")!r}).write_text("11111111-2222-3333-4444-555555555555", encoding="utf-8")
                        pathlib.Path(".agy_progress.md").write_text("resume me", encoding="utf-8")
                        print("SWITCH_ACCOUNT")
                    """
                ),
                encoding="utf-8",
            )
            agy_status.chmod(0o755)

            real_agy = bin_dir / "agy-bin"
            real_agy.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    state="{root / "agy-bin-ran"}"
                    printf '%s\\n' "$*" >> "{root / "agy-bin.log"}"
                    if [ ! -f "$state" ]; then
                        touch "$state"
                        exit 42
                    fi
                    printf 'RESUMED_OK\\n'
                    exit 0
                    """
                ),
                encoding="utf-8",
            )
            real_agy.chmod(0o755)

            env = os.environ.copy()
            env["HOME"] = str(home)
            env["AGY_DIR_OVERRIDE"] = str(agy_dir)
            result = subprocess.run(
                ["bash", str(wrapper), "-i", "initial prompt"],
                cwd=work,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("post-check", (root / "status.log").read_text(encoding="utf-8"))
            agy_bin_log = (root / "agy-bin.log").read_text(encoding="utf-8")
            self.assertIn("initial prompt", agy_bin_log)
            self.assertIn("--conversation 11111111-2222-3333-4444-555555555555", agy_bin_log)
            self.assertNotIn("compaction_rollover", agy_bin_log)
            self.assertNotIn("resume me", agy_bin_log)
            self.assertIn("RESUMED_OK", result.stdout)

    def test_interactive_clean_exit_still_checks_recent_quota_error(self):
        repo_root = Path(__file__).resolve().parents[1]
        wrapper = repo_root / "tools" / "agy" / "agy"

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            work = root / "work"
            agy_dir = root / "agy"
            bin_dir = home / ".local" / "bin"
            home.mkdir()
            work.mkdir()
            agy_dir.mkdir()
            bin_dir.mkdir(parents=True)

            agy_status = agy_dir / "agy-status.py"
            agy_status.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env python3
                    import pathlib
                    import sys

                    log = pathlib.Path({str(root / "status.log")!r})
                    command = sys.argv[1] if len(sys.argv) > 1 else ""
                    log.write_text(log.read_text() + command + "\\n" if log.exists() else command + "\\n")
                    if command == "post-check":
                        switched = pathlib.Path({str(root / "switched")!r})
                        if switched.exists():
                            sys.exit(1)
                        switched.touch()
                        pathlib.Path(".agy_progress.md").write_text("resume me", encoding="utf-8")
                        print("SWITCH_ACCOUNT")
                    """
                ),
                encoding="utf-8",
            )
            agy_status.chmod(0o755)

            real_agy = bin_dir / "agy-bin"
            real_agy.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    state="{root / "agy-bin-ran"}"
                    printf '%s\\n' "$*" >> "{root / "agy-bin.log"}"
                    if [ ! -f "$state" ]; then
                        touch "$state"
                        exit 0
                    fi
                    printf 'RESUMED_OK\\n'
                    exit 0
                    """
                ),
                encoding="utf-8",
            )
            real_agy.chmod(0o755)

            env = os.environ.copy()
            env["HOME"] = str(home)
            env["AGY_DIR_OVERRIDE"] = str(agy_dir)
            result = subprocess.run(
                ["bash", str(wrapper), "-i", "initial prompt"],
                cwd=work,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("post-check", (root / "status.log").read_text(encoding="utf-8"))
            agy_bin_log = (root / "agy-bin.log").read_text(encoding="utf-8")
            self.assertIn("initial prompt", agy_bin_log)
            self.assertNotIn("compaction_rollover", agy_bin_log)
            self.assertNotIn("resume me", agy_bin_log)
            self.assertIn("RESUMED_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
