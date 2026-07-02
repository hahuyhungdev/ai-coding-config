import os
import subprocess
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestAgyWrapper(unittest.TestCase):
    def test_interactive_exit_ignores_legacy_global_compact_signal(self):
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

            (agy_dir / ".compact_signal").touch()
            (agy_dir / ".active_conv_id").write_text("terminal-a-conversation", encoding="utf-8")

            agy_status = agy_dir / "agy-status.py"
            agy_status.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env python3
                    import os
                    import pathlib
                    import sys

                    log = pathlib.Path({str(root / "status.log")!r})
                    command = sys.argv[1] if len(sys.argv) > 1 else ""
                    log.write_text(log.read_text() + command + "\\n" if log.exists() else command + "\\n")
                    sys.exit(1)
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
                    printf '%s\\n' "$*" >> "{root / "agy-bin.log"}"
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
                ["bash", str(wrapper), "-i", "terminal b"],
                cwd=work,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout)
            agy_bin_log = (root / "agy-bin.log").read_text(encoding="utf-8")
            self.assertIn("terminal b", agy_bin_log)
            self.assertNotIn("terminal-a-conversation", agy_bin_log)
            self.assertNotIn("AUTO-RESUMING SESSION", result.stdout)

    def test_interactive_exit_resumes_from_own_session_state_dir(self):
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
                    import os
                    import pathlib
                    import sys

                    log = pathlib.Path({str(root / "status.log")!r})
                    command = sys.argv[1] if len(sys.argv) > 1 else ""
                    log.write_text(log.read_text() + command + "\\n" if log.exists() else command + "\\n")
                    if command == "post-check":
                        state_dir = pathlib.Path(os.environ["AGY_WRAPPER_STATE_DIR"])
                        (state_dir / ".active_conv_id").write_text("own-terminal-conversation", encoding="utf-8")
                        (state_dir / ".compact_signal").touch()
                        pathlib.Path(".agy_progress.md").write_text("own progress", encoding="utf-8")
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
                ["bash", str(wrapper), "-i", "terminal a"],
                cwd=work,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout)
            agy_bin_log = (root / "agy-bin.log").read_text(encoding="utf-8")
            self.assertIn("terminal a", agy_bin_log)
            self.assertIn("--conversation own-terminal-conversation", agy_bin_log)
            self.assertIn("RESUMED_OK", result.stdout)

    def test_wrapper_exports_stable_session_id_to_children(self):
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
                "#!/usr/bin/env python3\n",
                encoding="utf-8",
            )
            agy_status.chmod(0o755)

            real_agy = bin_dir / "agy-bin"
            real_agy.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    printf '%s\\n' "$AGY_WRAPPER_SESSION_ID" > "{root / "session-id.log"}"
                    printf '%s\\n' "$AGY_WRAPPER_STATE_DIR" > "{root / "state-dir.log"}"
                    exit 0
                    """
                ),
                encoding="utf-8",
            )
            real_agy.chmod(0o755)

            env = os.environ.copy()
            env["HOME"] = str(home)
            env["AGY_DIR_OVERRIDE"] = str(agy_dir)
            env["AGY_SESSION_ID_OVERRIDE"] = "terminal-a"
            result = subprocess.run(
                ["bash", str(wrapper), "-i", "session id check"],
                cwd=work,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual((root / "session-id.log").read_text(encoding="utf-8").strip(), "terminal-a")
            self.assertTrue((root / "state-dir.log").read_text(encoding="utf-8").strip().endswith("/terminal-a"))

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
                    import os
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
                        state_dir = pathlib.Path(os.environ["AGY_WRAPPER_STATE_DIR"])
                        (state_dir / ".active_conv_id").write_text("11111111-2222-3333-4444-555555555555", encoding="utf-8")
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
