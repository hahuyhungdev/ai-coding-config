import os
import sys
import unittest
import shutil
import json
import subprocess
import glob
from pathlib import Path

class TestAgyCliE2E(unittest.TestCase):
    def setUp(self):
        # Create fresh sandbox directory within the workspace directory to comply with rules
        self.workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.sandbox_dir = os.path.join(self.workspace_dir, "tests", "sandbox_cli_e2e")
        if os.path.exists(self.sandbox_dir):
            shutil.rmtree(self.sandbox_dir)
        os.makedirs(self.sandbox_dir, exist_ok=True)
        
        # Copy Python files from tools/agy to sandbox
        tools_agy_dir = os.path.join(self.workspace_dir, "tools", "agy")
        for filename in os.listdir(tools_agy_dir):
            if filename.endswith(".py"):
                shutil.copy2(
                    os.path.join(tools_agy_dir, filename),
                    os.path.join(self.sandbox_dir, filename)
                )

        # Create standard accounts.json
        self.accounts_data = [
            {
                "email": "user1@gmail.com",
                "auth_method": "consumer",
                "token": {"refresh_token": "token1", "access_token": "access1"},
                "quota": "100%",
                "status": "🟢 Ready"
            },
            {
                "email": "user2@gmail.com",
                "auth_method": "consumer",
                "token": {"refresh_token": "token2", "access_token": "access2"},
                "quota": "50%",
                "status": "🟢 Ready",
                "label": "UserTwoLabel"
            }
        ]
        self.accounts_file = os.path.join(self.sandbox_dir, "accounts.json")
        with open(self.accounts_file, "w") as f:
            json.dump(self.accounts_data, f, indent=2)
            
        # Create active token file pointing to user1
        self.token_file = os.path.join(self.sandbox_dir, "antigravity-oauth-token")
        with open(self.token_file, "w") as f:
            json.dump(self.accounts_data[0], f, indent=2)

    def tearDown(self):
        # Clean up sandbox
        if os.path.exists(self.sandbox_dir):
            shutil.rmtree(self.sandbox_dir)

    def run_agy(self, args, env_override=None):
        env = os.environ.copy()
        env["AGY_DIR_OVERRIDE"] = self.sandbox_dir
        if env_override:
            env.update(env_override)
        
        cmd = ["bash", os.path.join(self.workspace_dir, "tools", "agy", "agy")] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            cwd=self.workspace_dir
        )
        return result

    def test_list_commands(self):
        # 1. Verify agy list / ls / accounts (standard output)
        for cmd in ["list", "ls", "accounts"]:
            res = self.run_agy([cmd])
            self.assertEqual(res.returncode, 0)
            self.assertIn("user1@gmail.com *", res.stdout)
            self.assertIn("UserTwoLabel", res.stdout)

        # 2. Verify agy list --json
        res_json1 = self.run_agy(["list", "--json"])
        self.assertEqual(res_json1.returncode, 0)
        data1 = json.loads(res_json1.stdout)
        self.assertIn("accounts", data1)
        self.assertEqual(len(data1["accounts"]), 2)
        self.assertTrue(data1["accounts"][0]["active"])
        self.assertFalse(data1["accounts"][1]["active"])

        # 3. Verify agy --json list
        res_json2 = self.run_agy(["--json", "list"])
        self.assertEqual(res_json2.returncode, 0)
        data2 = json.loads(res_json2.stdout)
        self.assertEqual(data1, data2)

    def test_current_commands(self):
        # 1. Verify agy current (standard output)
        res = self.run_agy(["current"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Active account: user1@gmail.com", res.stdout)

        # 2. Verify agy current --json
        res_json = self.run_agy(["current", "--json"])
        self.assertEqual(res_json.returncode, 0)
        data = json.loads(res_json.stdout)
        self.assertIn("account", data)
        self.assertEqual(data["account"]["email"], "user1@gmail.com")
        self.assertTrue(data["account"]["active"])

    def test_add_commands(self):
        # 1. Verify agy add (imports active token)
        # Setup a token file representing a new/updated account to import
        import_token = {
            "email": "new_user@gmail.com",
            "auth_method": "consumer",
            "token": {"refresh_token": "tokenNew", "access_token": "accessNew"}
        }
        with open(self.token_file, "w") as f:
            json.dump(import_token, f, indent=2)

        res = self.run_agy(["add"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Successfully added new account 'new_user' to accounts.json!", res.stdout)

        # Verify added to accounts.json
        with open(self.accounts_file, "r") as f:
            accounts = json.load(f)
            emails = [acc.get("email") for acc in accounts]
            self.assertIn("new_user@gmail.com", emails)

        # 2. Verify agy add --label
        res_label = self.run_agy(["add", "--label", "CustomLabel"])
        self.assertEqual(res_label.returncode, 0)
        with open(self.accounts_file, "r") as f:
            accounts = json.load(f)
            new_acc = next(acc for acc in accounts if acc.get("email") == "new_user@gmail.com")
            self.assertEqual(new_acc.get("label"), "CustomLabel")

        # 3. Verify aliases: import and save
        for alias in ["import", "save"]:
            res_alias = self.run_agy([alias])
            self.assertEqual(res_alias.returncode, 0)
            self.assertIn("Successfully updated existing account", res_alias.stdout)

    def test_use_select_choose_commands(self):
        # 1. Verify agy use <target> works with index
        res = self.run_agy(["use", "2"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Switched active account to UserTwoLabel", res.stdout)
        
        # Verify active token file updated to user2
        with open(self.token_file, "r") as f:
            active_token = json.load(f)
            self.assertEqual(active_token["email"], "user2@gmail.com")

        # 2. Verify agy select <target> works with email
        res2 = self.run_agy(["select", "user1@gmail.com"])
        self.assertEqual(res2.returncode, 0)
        self.assertIn("Switched active account to user1@gmail.com", res2.stdout)
        with open(self.token_file, "r") as f:
            active_token = json.load(f)
            self.assertEqual(active_token["email"], "user1@gmail.com")

        # 3. Verify agy choose <target> works with label and --json
        res3 = self.run_agy(["choose", "UserTwoLabel", "--json"])
        self.assertEqual(res3.returncode, 0)
        data = json.loads(res3.stdout)
        self.assertEqual(data["account"]["email"], "user2@gmail.com")

    def test_rename_command(self):
        # 1. Verify rename (standard output)
        res = self.run_agy(["rename", "1", "SuperUser1"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Renamed account user1@gmail.com to 'SuperUser1'", res.stdout)
        self.assertIn("Backup:", res.stdout)
        
        # Verify renamed in storage
        with open(self.accounts_file, "r") as f:
            accounts = json.load(f)
            self.assertEqual(accounts[0]["label"], "SuperUser1")

        # 2. Verify rename with --json
        res_json = self.run_agy(["rename", "user2@gmail.com", "SuperUser2", "--json"])
        self.assertEqual(res_json.returncode, 0)
        data = json.loads(res_json.stdout)
        self.assertEqual(data["account"]["label"], "SuperUser2")
        self.assertIn("backup", data)

    def test_remove_commands(self):
        # 1. Verify agy remove target fails without --yes
        res = self.run_agy(["remove", "UserTwoLabel"])
        self.assertEqual(res.returncode, 1)
        self.assertIn("Error: Account removal requires --yes", res.stderr)
        
        # Verify target not removed
        with open(self.accounts_file, "r") as f:
            self.assertEqual(len(json.load(f)), 2)

        # 2. Verify agy remove target --yes works and creates backup
        res2 = self.run_agy(["remove", "UserTwoLabel", "--yes"])
        self.assertEqual(res2.returncode, 0)
        self.assertIn("Removed account UserTwoLabel (user2@gmail.com)", res2.stdout)
        self.assertIn("Backup:", res2.stdout)

        # Verify removed in storage
        with open(self.accounts_file, "r") as f:
            accounts = json.load(f)
            self.assertEqual(len(accounts), 1)
            self.assertEqual(accounts[0]["email"], "user1@gmail.com")

        # Verify backup exists
        backups = glob.glob(os.path.join(self.sandbox_dir, "backups", "accounts-*.json"))
        self.assertTrue(len(backups) >= 1)

        # 3. Verify delete-account alias works
        # Re-add user2 first by resetting accounts.json to self.accounts_data
        with open(self.accounts_file, "w") as f:
            json.dump(self.accounts_data, f)
            
        res3 = self.run_agy(["delete-account", "user2@gmail.com", "--yes"])
        self.assertEqual(res3.returncode, 0)
        self.assertIn("Removed account", res3.stdout)
        self.assertIn("user2@gmail.com", res3.stdout)

        # 4. Verify rm alias works
        with open(self.accounts_file, "w") as f:
            json.dump(self.accounts_data, f)

        res4 = self.run_agy(["rm", "user2@gmail.com", "--yes"])
        self.assertEqual(res4.returncode, 0)
        self.assertIn("Removed account", res4.stdout)
        self.assertIn("user2@gmail.com", res4.stdout)

    def test_doctor_command(self):
        # 1. Standard output
        res = self.run_agy(["doctor"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("AGY account health: OK", res.stdout)
        self.assertIn("Accounts: 2", res.stdout)

        # 2. JSON output
        res_json = self.run_agy(["doctor", "--json"])
        self.assertEqual(res_json.returncode, 0)
        data = json.loads(res_json.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["account_count"], 2)
        self.assertEqual(data["issues"], [])

    def test_backup_and_restore_commands(self):
        # 1. Backup: standard & custom output path
        res_backup1 = self.run_agy(["backup"])
        self.assertEqual(res_backup1.returncode, 0)
        self.assertIn("Backup created:", res_backup1.stdout)
        
        custom_backup_path = os.path.join(self.sandbox_dir, "my_custom_backup.json")
        res_backup2 = self.run_agy(["backup", "--out", custom_backup_path])
        self.assertEqual(res_backup2.returncode, 0)
        self.assertTrue(os.path.exists(custom_backup_path))

        # Modify accounts on disk to check restore
        modified_data = [{"email": "hacked@gmail.com", "token": {"refresh_token": "hacked_token"}}]
        with open(self.accounts_file, "w") as f:
            json.dump(modified_data, f)

        # 2. Restore: fails without --yes
        res_restore_fail = self.run_agy(["restore"])
        self.assertEqual(res_restore_fail.returncode, 1)
        self.assertIn("Error: Restore requires --yes", res_restore_fail.stderr)

        # 3. Restore: latest backup first (recovers original 2 accounts)
        res_restore_latest = self.run_agy(["restore", "--yes"])
        self.assertEqual(res_restore_latest.returncode, 0)
        with open(self.accounts_file, "r") as f:
            restored = json.load(f)
            self.assertEqual(len(restored), 2)
            self.assertEqual(restored[0]["email"], "user1@gmail.com")

        # Modify again to hacked
        with open(self.accounts_file, "w") as f:
            json.dump(modified_data, f)

        # 4. Restore: specific path
        res_restore_spec = self.run_agy(["restore", custom_backup_path, "--yes"])
        self.assertEqual(res_restore_spec.returncode, 0)
        self.assertIn("Accounts restored from:", res_restore_spec.stdout)
        
        with open(self.accounts_file, "r") as f:
            restored = json.load(f)
            self.assertEqual(len(restored), 2)
            self.assertEqual(restored[0]["email"], "user1@gmail.com")

    def test_clean_commands(self):
        # Setup dummy session history and files
        conversations_dir = os.path.join(self.sandbox_dir, "conversations")
        brain_dir = os.path.join(self.sandbox_dir, "brain")
        os.makedirs(conversations_dir, exist_ok=True)
        os.makedirs(brain_dir, exist_ok=True)

        history_file = os.path.join(self.sandbox_dir, "history.jsonl")
        active_uuid = "11111111-2222-3333-4444-555555555555"
        inactive_uuid = "99999999-8888-7777-6666-555555555555"

        with open(history_file, "w") as f:
            f.write(json.dumps({"conversationId": active_uuid}) + "\n")

        # Create active files
        open(os.path.join(conversations_dir, f"{active_uuid}.db"), "w").close()
        os.makedirs(os.path.join(brain_dir, active_uuid), exist_ok=True)
        open(os.path.join(brain_dir, active_uuid, "log.txt"), "w").close()

        # Create inactive (orphaned) files
        open(os.path.join(conversations_dir, f"{inactive_uuid}.db"), "w").close()
        os.makedirs(os.path.join(brain_dir, inactive_uuid), exist_ok=True)
        open(os.path.join(brain_dir, inactive_uuid, "log.txt"), "w").close()

        # 1. Verify agy clean (standard output)
        res = self.run_agy(["clean"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Cleaned up 1 automated/orphaned sessions", res.stdout)
        
        # Verify inactive files removed, active files remain
        self.assertFalse(os.path.exists(os.path.join(conversations_dir, f"{inactive_uuid}.db")))
        self.assertFalse(os.path.exists(os.path.join(brain_dir, inactive_uuid)))
        self.assertTrue(os.path.exists(os.path.join(conversations_dir, f"{active_uuid}.db")))
        self.assertTrue(os.path.exists(os.path.join(brain_dir, active_uuid)))

        # 2. Verify clean --json with another set of orphaned files
        open(os.path.join(conversations_dir, f"{inactive_uuid}.db"), "w").close()
        os.makedirs(os.path.join(brain_dir, inactive_uuid), exist_ok=True)
        open(os.path.join(brain_dir, inactive_uuid, "log.txt"), "w").close()

        res_json = self.run_agy(["clean", "--json"])
        self.assertEqual(res_json.returncode, 0)
        data = json.loads(res_json.stdout)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["cleaned_count"], 1)

        # 3. Verify cleanup and prune aliases
        for alias in ["cleanup", "prune"]:
            open(os.path.join(conversations_dir, f"{inactive_uuid}.db"), "w").close()
            os.makedirs(os.path.join(brain_dir, inactive_uuid), exist_ok=True)
            res_alias = self.run_agy([alias])
            self.assertEqual(res_alias.returncode, 0)
            self.assertIn("Cleaned up 1", res_alias.stdout)

    def test_typo_suggestions(self):
        # 1. Top-level typo
        res = self.run_agy(["statu"])
        self.assertEqual(res.returncode, 2)
        self.assertIn("Unknown command: statu", res.stderr)
        self.assertIn("Did you mean:", res.stderr)
        self.assertIn("agy status", res.stderr)

        # 2. Nested typo
        res_nested = self.run_agy(["account", "statu"])
        self.assertEqual(res_nested.returncode, 2)
        self.assertIn("Unknown command: statu", res_nested.stderr)
        self.assertIn("Did you mean:", res_nested.stderr)
        self.assertIn("agy account status", res_nested.stderr)

    def test_help_commands(self):
        # 1. agy status --help
        res1 = self.run_agy(["status", "--help"])
        self.assertEqual(res1.returncode, 0)
        self.assertIn("usage: agy status", res1.stdout)

        # 2. agy help status
        res2 = self.run_agy(["help", "status"])
        self.assertEqual(res2.returncode, 0)
        self.assertIn("usage: agy status", res2.stdout)

        # 3. agy help
        res3 = self.run_agy(["help"])
        self.assertEqual(res3.returncode, 0)
        self.assertIn("usage: agy", res3.stdout)

    def test_flag_positions(self):
        # 1. agy --json list vs agy list --json
        res1 = self.run_agy(["--json", "list"])
        res2 = self.run_agy(["list", "--json"])
        self.assertEqual(res1.returncode, 0)
        self.assertEqual(res2.returncode, 0)
        self.assertEqual(json.loads(res1.stdout), json.loads(res2.stdout))

        # 2. --json error shapes with different flag positions
        res3 = self.run_agy(["--json", "remove", "user1@gmail.com"])
        res4 = self.run_agy(["remove", "user1@gmail.com", "--json"])
        self.assertEqual(res3.returncode, 1)
        self.assertEqual(res4.returncode, 1)
        
        data3 = json.loads(res3.stdout)
        data4 = json.loads(res4.stdout)
        self.assertEqual(data3, data4)
        self.assertEqual(data3["error"], "Account removal requires --yes")

if __name__ == "__main__":
    unittest.main()
