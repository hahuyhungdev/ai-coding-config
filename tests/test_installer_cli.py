import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parent.parent


class TestInstallerCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.project = self.root / "project"
        self.bin = self.root / "bin"
        self.home.mkdir()
        self.project.mkdir()
        self.bin.mkdir()
        self._write_executable(
            "graphify",
            """#!/bin/sh
echo "$@" >> graphify_args.txt
if [ "$1" = "update" ]; then
  mkdir -p graphify-out
  printf '{}' > graphify-out/graph.json
fi
exit 0
""",
            r"""@echo off
echo %* >> graphify_args.txt
if "%1" == "update" (
  mkdir graphify-out 2>nul
  echo {} > graphify-out\graph.json
)
exit /b 0
"""
        )
        for executable in ("claude", "codex", "agy", "node"):
            self._write_executable(executable, "#!/bin/sh\nexit 0\n", "@echo off\nexit /b 0\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _write_executable(self, name, bash_content, bat_content=None):
        if sys.platform == "win32":
            path = self.bin / f"{name}.bat"
            path.write_text(bat_content or "@echo off\nexit /b 0\n")
        else:
            path = self.bin / name
            path.write_text(bash_content)
            path.chmod(0o755)

    def _run(self, *args, include_graphify=True):
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        # Windows uses USERPROFILE for Path.home(), not HOME
        if sys.platform == "win32":
            env["USERPROFILE"] = str(self.home)
        # Build PATH: test bin first, then system dirs (excluding dirs with real graphify if not wanted)
        sep = os.pathsep
        system_path = os.environ.get("PATH", "")
        if not include_graphify:
            # Filter out system dirs that contain a real graphify binary
            real_graphify = shutil.which("graphify")
            if real_graphify:
                graphify_dir = str(Path(real_graphify).parent)
                system_path = sep.join(
                    d for d in system_path.split(sep) if Path(d) != Path(graphify_dir)
                )
        env["PATH"] = str(self.bin) + sep + system_path
        
        ext = ".bat" if sys.platform == "win32" else ""
        graphify_bin = self.bin / f"graphify{ext}"
        disabled_bin = self.bin / f"graphify.disabled{ext}"
        
        if not include_graphify and graphify_bin.exists():
            graphify_bin.rename(disabled_bin)
        try:
            return subprocess.run(
                [sys.executable, str(REPO_DIR / "install.py"), *args, "--project", str(self.project)],
                cwd=self.project,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
        finally:
            if not include_graphify and disabled_bin.exists():
                disabled_bin.rename(graphify_bin)

    def _run_agy(self, *args):
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        if sys.platform == "win32":
            env["USERPROFILE"] = str(self.home)
        sep = os.pathsep
        env["PATH"] = str(self.bin) + sep + os.environ.get("PATH", "")
        return subprocess.run(
            [sys.executable, str(REPO_DIR / "install-agy.py"), *args],
            cwd=self.project,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def _run_global_uninstall(self):
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        if sys.platform == "win32":
            env["USERPROFILE"] = str(self.home)
        env["PATH"] = str(self.bin) + os.pathsep + os.environ.get("PATH", "")
        return subprocess.run(
            [sys.executable, str(REPO_DIR / "install.py"), "--uninstall"],
            cwd=self.project,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def _run_installed_agy(self, *args, stdin=None):
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        if sys.platform == "win32":
            env["USERPROFILE"] = str(self.home)
        env["PATH"] = str(self.home / ".local" / "bin") + os.pathsep + str(self.bin) + os.pathsep + os.environ.get("PATH", "")
        return subprocess.run(
            [str(self.home / ".local" / "bin" / "agy"), *args],
            cwd=self.project,
            env=env,
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
        )

    def _seed_agy_accounts(self):
        agy_dir = self.home / ".gemini" / "antigravity-cli"
        accounts = [
            {
                "email": "first@example.com",
                "label": "first",
                "auth_method": "consumer",
                "token": {"refresh_token": "rt-1"},
                "status": "🟢 Ready",
                "quota": "5H:90%/W:80%",
                "reset_info": "5H:Ready/W:Fri 10:00",
            },
            {
                "email": "second@example.com",
                "auth_method": "consumer",
                "token": {"refresh_token": "rt-2"},
                "status": "🟢 Ready",
                "quota": "5H:100%/W:90%",
                "reset_info": "5H:Ready/W:Sun 09:00",
            },
        ]
        (agy_dir / "accounts.json").write_text(json.dumps(accounts))
        (agy_dir / "antigravity-oauth-token").write_text(json.dumps(accounts[0]))
        return agy_dir, accounts

    def test_all_force_is_idempotent(self):
        first = self._run("--all", "--force")
        self.assertEqual(first.returncode, 0, first.stderr)
        paths = [
            self.project / ".claude" / "settings.json",
            self.project / ".codex" / "hooks.json",
        ]
        before = {path: path.read_text() for path in paths}

        second = self._run("--all", "--force")

        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(before, {path: path.read_text() for path in paths})
        for path in paths:
            json.loads(path.read_text())

    def test_individual_cli_flags_only_configure_selected_project(self):
        cases = {
            "--claude": self.project / ".claude" / "settings.json",
            "--codex": self.project / ".codex" / "hooks.json",
        }
        for flag, expected in cases.items():
            with self.subTest(flag=flag):
                for name in (".claude", ".codex"):
                    target = self.project / name
                    if target.exists():
                        import shutil
                        shutil.rmtree(target)
                result = self._run(flag, "--force")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(expected.exists())
                created = [name for name in (".claude", ".codex") if (self.project / name).exists()]
                self.assertEqual(created, [expected.parent.name])

    def test_none_does_not_configure_project_assistants(self):
        result = self._run("--none", "--force")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.project / ".claude").exists())
        self.assertFalse((self.project / ".codex").exists())

    def test_missing_graphify_falls_back_without_project_hooks(self):
        import sys
        ext = ".bat" if sys.platform == "win32" else ""
        (self.bin / f"graphify{ext}").unlink()
        result = self._run("--all", "--force", include_graphify=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.project / "graphify-out").exists())
        self.assertFalse((self.project / ".claude").exists())

    def test_installs_global_cli_wrapper(self):
        result = self._run("--all", "--force")
        self.assertEqual(result.returncode, 0, result.stderr)
        
        # 1. Unix wrapper
        bash_path = self.home / ".local" / "bin" / "ai-config"
        self.assertTrue(bash_path.is_file())
        self.assertIn("install.py", bash_path.read_text())
        self.assertIn("init", bash_path.read_text())
        self.assertTrue(os.access(bash_path, os.X_OK))

        # 2. Windows wrapper
        bat_path = self.home / ".local" / "bin" / "ai-config.bat"
        self.assertTrue(bat_path.is_file())
        self.assertIn("install.py", bat_path.read_text())
        self.assertIn("init", bat_path.read_text())

    def test_global_install_configures_rtk_for_claude_and_codex(self):
        result = self._run("--all", "--force")
        self.assertEqual(result.returncode, 0, result.stderr)

        claude_settings = json.loads((self.home / ".claude" / "settings.json").read_text())
        pre_tool_hooks = claude_settings["hooks"]["PreToolUse"]
        self.assertTrue(
            any(
                hook.get("matcher") == "Bash"
                and any(command.get("command") == "rtk hook claude" for command in hook.get("hooks", []))
                for hook in pre_tool_hooks
            )
        )

        codex_agents = (self.home / ".codex" / "AGENTS.md").read_text()
        self.assertIn(f"@{self.home / '.codex' / 'RTK.md'}", codex_agents)

        antigravity_rules = self.project / ".agents" / "rules" / "antigravity-rtk-rules.md"
        self.assertTrue(antigravity_rules.is_file())
        self.assertIn("Always prefix shell commands with `rtk`", antigravity_rules.read_text())

    def test_global_install_copies_gemini_skills_and_configs(self):
        result = self._run("--all", "--force")
        self.assertEqual(result.returncode, 0, result.stderr)

        # Gemini
        gemini_dir = self.home / ".gemini" / "config"
        self.assertTrue((gemini_dir / "ANTIGRAVITY.md").is_file())
        self.assertTrue((gemini_dir / "skills").is_dir())
        self.assertTrue((gemini_dir / "skills" / "context-budget" / "SKILL.md").is_file())
        self.assertTrue((gemini_dir / "agents").is_dir())

        # Claude & Codex skills check for consistency
        self.assertTrue((self.home / ".claude" / "skills" / "context-budget" / "SKILL.md").is_file())
        self.assertTrue((self.home / ".codex" / "skills" / "context-budget" / "SKILL.md").is_file())

    def test_setup_agy_installs_wrappers(self):
        result = self._run_agy()
        self.assertEqual(result.returncode, 0, result.stderr)
        
        # Check that agy wrapper script is installed to ~/.local/bin/agy
        agy_wrapper = self.home / ".local" / "bin" / "agy"
        self.assertTrue(agy_wrapper.is_file())
        self.assertTrue(os.access(agy_wrapper, os.X_OK))
        
        # Check that agy-status.py is installed to ~/.gemini/antigravity-cli/agy-status.py
        agy_status = self.home / ".gemini" / "antigravity-cli" / "agy-status.py"
        self.assertTrue(agy_status.is_file())
        agy_readme = self.home / ".gemini" / "antigravity-cli" / "README.md"
        self.assertTrue(agy_readme.is_file())
        self.assertIn("Module Map", agy_readme.read_text())

    def test_add_current_account_alias_bootstraps_missing_account_pool(self):
        install = self._run_agy()
        self.assertEqual(install.returncode, 0, install.stderr)

        agy_dir = self.home / ".gemini" / "antigravity-cli"
        token = {
            "email": "first@example.com",
            "auth_method": "consumer",
            "token": {"refresh_token": "refresh-token"},
        }
        (agy_dir / "antigravity-oauth-token").write_text(json.dumps(token))

        env = os.environ.copy()
        env["HOME"] = str(self.home)
        if sys.platform == "win32":
            env["USERPROFILE"] = str(self.home)
        env["PATH"] = str(self.home / ".local" / "bin") + os.pathsep + str(self.bin) + os.pathsep + os.environ.get("PATH", "")
        result = subprocess.run(
            [str(self.home / ".local" / "bin" / "agy"), "add-current-account"],
            cwd=self.project,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        accounts = json.loads((agy_dir / "accounts.json").read_text())
        self.assertEqual(accounts[0]["email"], "first@example.com")
        self.assertEqual(accounts[0]["token"]["refresh_token"], "refresh-token")

    def test_agy_account_commands_and_status_refresh(self):
        install = self._run_agy()
        self.assertEqual(install.returncode, 0, install.stderr)
        agy_dir, _ = self._seed_agy_accounts()

        cached = self._run_installed_agy("account", "list")
        status = self._run_installed_agy("status")
        current = self._run_installed_agy("account", "current")
        use = self._run_installed_agy("account", "use", "2")
        rename = self._run_installed_agy("account", "rename", "2", "work")

        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn("Checking status", status.stdout)
        self.assertEqual(cached.returncode, 0, cached.stderr)
        self.assertIn("5H:90%/W:80%", cached.stdout)
        self.assertNotIn("Checking status", cached.stdout)
        self.assertEqual(current.returncode, 0, current.stderr)
        self.assertIn("first@example.com", current.stdout)
        self.assertEqual(use.returncode, 0, use.stderr)
        self.assertEqual(rename.returncode, 0, rename.stderr)
        accounts = json.loads((agy_dir / "accounts.json").read_text())
        self.assertEqual(accounts[1]["email"], "second@example.com")
        self.assertEqual(accounts[1]["label"], "work")
        self.assertTrue(list((agy_dir / "backups").glob("accounts-*.json")))

    def test_agy_remove_requires_confirmation_and_creates_backup(self):
        install = self._run_agy()
        self.assertEqual(install.returncode, 0, install.stderr)
        agy_dir, _ = self._seed_agy_accounts()

        refused = self._run_installed_agy("account", "remove", "2")
        removed = self._run_installed_agy("account", "remove", "2", "--yes")

        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("--yes", refused.stderr + refused.stdout)
        self.assertEqual(removed.returncode, 0, removed.stderr)
        accounts = json.loads((agy_dir / "accounts.json").read_text())
        self.assertEqual(len(accounts), 1)
        self.assertTrue(list((agy_dir / "backups").glob("accounts-*.json")))

    def test_agy_account_add_label_preserves_authenticated_email(self):
        install = self._run_agy()
        self.assertEqual(install.returncode, 0, install.stderr)
        agy_dir = self.home / ".gemini" / "antigravity-cli"
        token = {
            "email": "owner@example.com",
            "auth_method": "consumer",
            "token": {"refresh_token": "owner-token"},
        }
        (agy_dir / "antigravity-oauth-token").write_text(json.dumps(token))

        result = self._run_installed_agy("account", "add", "--label", "personal")

        self.assertEqual(result.returncode, 0, result.stderr)
        account = json.loads((agy_dir / "accounts.json").read_text())[0]
        self.assertEqual(account["email"], "owner@example.com")
        self.assertEqual(account["label"], "personal")

    def test_removing_active_account_activates_remaining_account(self):
        install = self._run_agy()
        self.assertEqual(install.returncode, 0, install.stderr)
        agy_dir, _ = self._seed_agy_accounts()

        result = self._run_installed_agy("account", "remove", "1", "--yes")

        self.assertEqual(result.returncode, 0, result.stderr)
        active = json.loads((agy_dir / "antigravity-oauth-token").read_text())
        self.assertEqual(active["token"]["refresh_token"], "rt-2")

    def test_agy_json_doctor_and_account_list_redact_tokens(self):
        install = self._run_agy()
        self.assertEqual(install.returncode, 0, install.stderr)
        self._seed_agy_accounts()

        doctor = self._run_installed_agy("--json", "doctor")
        listed = self._run_installed_agy("--json", "account", "list")

        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        doctor_data = json.loads(doctor.stdout)
        self.assertTrue(doctor_data["ok"])
        self.assertEqual(doctor_data["account_count"], 2)
        self.assertNotIn("rt-1", doctor.stdout)
        self.assertEqual(listed.returncode, 0, listed.stderr)
        list_data = json.loads(listed.stdout)
        self.assertEqual(list_data["accounts"][0]["email"], "first@example.com")
        self.assertNotIn("refresh_token", listed.stdout)
        self.assertNotIn("rt-1", listed.stdout)

    def test_agy_backup_and_restore_round_trip(self):
        install = self._run_agy()
        self.assertEqual(install.returncode, 0, install.stderr)
        agy_dir, original = self._seed_agy_accounts()

        backup = self._run_installed_agy("--json", "backup")
        backup_data = json.loads(backup.stdout)
        (agy_dir / "accounts.json").write_text("[]")
        restore = self._run_installed_agy("restore", backup_data["path"], "--yes")

        self.assertEqual(backup.returncode, 0, backup.stderr)
        self.assertEqual(restore.returncode, 0, restore.stderr)
        self.assertEqual(json.loads((agy_dir / "accounts.json").read_text()), original)

    def test_agy_help_documents_new_command_surface(self):
        install = self._run_agy()
        self.assertEqual(install.returncode, 0, install.stderr)

        result = self._run_installed_agy("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        for command in ("account", "status", "doctor", "backup", "restore"):
            self.assertIn(command, result.stdout)

    def test_agy_unknown_command_suggests_without_launching_cli(self):
        install = self._run_agy()
        self.assertEqual(install.returncode, 0, install.stderr)

        result = self._run_installed_agy("s")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown command: s", result.stderr)
        self.assertIn("agy status", result.stderr)
        self.assertNotIn("agy restore", result.stderr)
        self.assertNotIn("REAL_AGY_CALLED", result.stdout + result.stderr)

    def test_agy_typo_suggests_top_level_and_nested_commands(self):
        install = self._run_agy()
        self.assertEqual(install.returncode, 0, install.stderr)

        top_level = self._run_installed_agy("acount", "list")
        nested = self._run_installed_agy("account", "lits")

        self.assertNotEqual(top_level.returncode, 0)
        self.assertIn("agy account", top_level.stderr)
        self.assertNotIn("agy backup", top_level.stderr)
        self.assertNotEqual(nested.returncode, 0)
        self.assertIn("agy account list", nested.stderr)
        self.assertNotIn("agy account use", nested.stderr)

    def test_agy_valid_flags_still_pass_through_to_real_cli(self):
        install = self._run_agy()
        self.assertEqual(install.returncode, 0, install.stderr)
        real_agy = self.home / ".local" / "bin" / "agy-bin"
        real_agy.write_text("#!/bin/sh\nprintf 'REAL_AGY_CALLED:%s\\n' \"$*\"\n")
        real_agy.chmod(0o755)

        result = self._run_installed_agy("-p", "hello")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("REAL_AGY_CALLED:-p hello", result.stdout)

    def test_bare_agy_still_launches_interactive_cli(self):
        install = self._run_agy()
        self.assertEqual(install.returncode, 0, install.stderr)
        real_agy = self.home / ".local" / "bin" / "agy-bin"
        real_agy.write_text("#!/bin/sh\nprintf 'REAL_AGY_CALLED:%s\\n' \"$*\"\n")
        real_agy.chmod(0o755)

        result = self._run_installed_agy()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("REAL_AGY_CALLED:", result.stdout)

    def test_native_agy_subcommands_still_pass_through(self):
        install = self._run_agy()
        self.assertEqual(install.returncode, 0, install.stderr)
        real_agy = self.home / ".local" / "bin" / "agy-bin"
        real_agy.write_text("#!/bin/sh\nprintf 'REAL_AGY_CALLED:%s\\n' \"$*\"\n")
        real_agy.chmod(0o755)

        for args in (
            ("changelog",),
            ("install",),
            ("models",),
            ("plugin", "list"),
            ("plugins", "list"),
            ("update",),
            ("help", "models"),
        ):
            with self.subTest(args=args):
                result = self._run_installed_agy(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"REAL_AGY_CALLED:{' '.join(args)}", result.stdout)

    def test_agy_help_subcommands(self):
        install = self._run_agy()
        self.assertEqual(install.returncode, 0, install.stderr)
        real_agy = self.home / ".local" / "bin" / "agy-bin"
        real_agy.write_text("#!/bin/sh\nprintf 'REAL_AGY_CALLED:%s\\n' \"$*\"\n")
        real_agy.chmod(0o755)

        # help status should show status help (runs agy-status.py)
        result = self._run_installed_agy("help", "status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--refresh", result.stdout)

        # help models should bypass and run agy-bin (runs real agy-bin)
        result2 = self._run_installed_agy("help", "models")
        self.assertEqual(result2.returncode, 0, result2.stderr)
        self.assertIn("REAL_AGY_CALLED:help models", result2.stdout)

    def test_agy_uninstall_preserves_user_account_data(self):
        install = self._run_agy()
        self.assertEqual(install.returncode, 0, install.stderr)

        agy_dir = self.home / ".gemini" / "antigravity-cli"
        user_files = {
            "accounts.json": "[]",
            "accounts-backup.json": "[]",
            "antigravity-oauth-token": "{}",
            "history.jsonl": "",
            "settings.json": "{}",
        }
        for name, content in user_files.items():
            (agy_dir / name).write_text(content)

        uninstall = self._run_agy("--uninstall")

        self.assertEqual(uninstall.returncode, 0, uninstall.stderr)
        self.assertFalse((agy_dir / "agy-status.py").exists())
        for name in user_files:
            self.assertTrue((agy_dir / name).exists(), name)

    def test_global_uninstall_preserves_user_account_data(self):
        install = self._run("--all", "--force")
        self.assertEqual(install.returncode, 0, install.stderr)

        agy_dir = self.home / ".gemini" / "antigravity-cli"
        agy_dir.mkdir(parents=True, exist_ok=True)
        (agy_dir / "agy-status.py").write_text("managed")
        user_files = {
            "accounts.json": "[]",
            "accounts-backup.json": "[]",
            "antigravity-oauth-token": "{}",
            "history.jsonl": "",
            "settings.json": "{}",
        }
        for name, content in user_files.items():
            (agy_dir / name).write_text(content)

        uninstall = self._run_global_uninstall()

        self.assertEqual(uninstall.returncode, 0, uninstall.stderr)
        self.assertFalse((agy_dir / "agy-status.py").exists())
        for name in user_files:
            self.assertTrue((agy_dir / name).exists(), name)

    def test_init_ai_forwards_unknown_arguments(self):
        log_path = self.project / "graphify_args.txt"
        if log_path.exists():
            log_path.unlink()
            
        result = self._run("--init-ai", "--backend", "gemini-cli", "--max-concurrency", "4", "--token-budget", "120000")
        self.assertEqual(result.returncode, 0, result.stderr)
        
        self.assertTrue(log_path.exists())
        args_logged = log_path.read_text().strip()
        self.assertIn("extract . --mode deep --backend gemini-cli", args_logged)
        self.assertIn("--max-concurrency 4", args_logged)
        self.assertIn("--token-budget 120000", args_logged)

    def test_unrecognized_arguments_fail_on_standard_run(self):
        result = self._run("--claude", "--max-concurrency", "4")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unrecognized arguments", result.stderr)


if __name__ == "__main__":
    unittest.main()
