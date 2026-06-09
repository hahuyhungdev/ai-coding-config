import os
import sys
import json
import subprocess
import unittest
from pathlib import Path

# Try to import tomllib (Python 3.11+) or fallback to pip package if needed
try:
    import tomllib
except ImportError:
    tomllib = None

REPO_DIR = Path(__file__).resolve().parent.parent


class TestAiCodingConfig(unittest.TestCase):

    def test_configuration_syntax(self):
        """Validate syntax of config templates in the repository."""
        # 1. Claude global settings
        claude_settings = REPO_DIR / "claude" / "settings.json"
        self.assertTrue(claude_settings.exists())
        with open(claude_settings, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertIn("permissions", data)

        # 2. Gemini global settings
        gemini_settings = REPO_DIR / "gemini" / "settings.json"
        self.assertTrue(gemini_settings.exists())
        with open(gemini_settings, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertIn("trustedWorkspaces", data)

        # 3. Codex global settings
        codex_config = REPO_DIR / "codex" / "config.toml"
        self.assertTrue(codex_config.exists())
        if tomllib:
            with open(codex_config, "rb") as f:
                data = tomllib.load(f)
                self.assertIn("approval_policy", data)

    def test_generated_project_hooks_syntax(self):
        """Validate syntax of generated project-level hook configuration files."""
        # Claude project settings
        claude_proj = REPO_DIR / ".claude" / "settings.json"
        self.assertTrue(claude_proj.exists(), "Claude project settings.json does not exist. Run installer first.")
        with open(claude_proj, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertIn("hooks", data)
            self.assertIn("PreToolUse", data["hooks"])

        # Gemini project settings
        gemini_proj = REPO_DIR / ".gemini" / "settings.json"
        self.assertTrue(gemini_proj.exists(), "Gemini project settings.json does not exist. Run installer first.")
        with open(gemini_proj, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertIn("hooks", data)
            self.assertIn("BeforeTool", data["hooks"])

        # Codex project hooks
        codex_proj = REPO_DIR / ".codex" / "hooks.json"
        self.assertTrue(codex_proj.exists(), "Codex project hooks.json does not exist. Run installer first.")
        with open(codex_proj, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertIn("hooks", data)
            self.assertIn("PreToolUse", data["hooks"])

    def test_gemini_before_tool_hook_filtering(self):
        """Test the path-filtering and ignoring logic in the Gemini BeforeTool hook."""
        gemini_proj = REPO_DIR / ".gemini" / "settings.json"
        with open(gemini_proj, "r", encoding="utf-8") as f:
            settings = json.load(f)
            
        hook_cmd = settings["hooks"]["BeforeTool"][0]["hooks"][0]["command"]
        self.assertTrue(hook_cmd.startswith("python3 -c"))
        
        # Extract python code string
        # Casing of python3 -c '...' has single quotes
        start_idx = hook_cmd.find("'")
        end_idx = hook_cmd.rfind("'")
        py_code = hook_cmd[start_idx + 1:end_idx]
        
        def run_hook_py(tool_input):
            p = subprocess.Popen(
                [sys.executable, "-c", py_code],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = p.communicate(input=json.dumps({"tool_input": tool_input}))
            return json.loads(stdout)

        # Case 1: Source code file -> Should match and return deny with graphify instructions
        res = run_hook_py({"path": "install.py"})
        self.assertEqual(res.get("decision"), "deny")
        self.assertIn("additionalContext", res)
        self.assertIn("BLOCKED by graphify hook", res["additionalContext"])
        self.assertIn("graphify query", res["additionalContext"])

        # Case 2: Config/skill file -> Should NOT match additionalContext
        res = run_hook_py({"path": "skills/frontend-design/SKILL.md"})
        self.assertEqual(res.get("decision"), "allow")
        self.assertNotIn("additionalContext", res)

        # Case 3: Ignored path (graphify-out) -> Should NOT match additionalContext
        res = run_hook_py({"path": "graphify-out/graph.json"})
        self.assertEqual(res.get("decision"), "allow")
        self.assertNotIn("additionalContext", res)

        # Case 4: Another source file -> Should match and return deny with graphify instructions
        res = run_hook_py({"path": "src/main.go"})
        self.assertEqual(res.get("decision"), "deny")
        self.assertIn("additionalContext", res)
        self.assertIn("BLOCKED by graphify hook", res["additionalContext"])

    def test_claude_pre_tool_hook_filtering(self):
        """Test the path-filtering logic in the Claude PreToolUse hook."""
        claude_proj = REPO_DIR / ".claude" / "settings.json"
        with open(claude_proj, "r", encoding="utf-8") as f:
            settings = json.load(f)
            
        # Extract Read|Glob hook command
        hook_cmd = None
        for h in settings["hooks"]["PreToolUse"]:
            if h["matcher"] == "Read|Glob":
                hook_cmd = h["hooks"][0]["command"]
                break
                
        self.assertIsNotNone(hook_cmd)
        
        # The hook runs a python snippet to compute HIT: HIT=$(python3 -c "...")
        # Let's extract the python command inside HIT=$(...)
        # It is python3 -c "..."
        py_start = hook_cmd.find("python3 -c")
        py_end = hook_cmd.find(" 2>/dev/null")
        py_part = hook_cmd[py_start:py_end]
        
        # Remove python3 -c and surrounding quotes
        start_q = py_part.find('"')
        end_q = py_part.rfind('"')
        py_code = py_part[start_q + 1:end_q].replace('\\"', '"')

        def run_hook_py(tool_input):
            p = subprocess.Popen(
                [sys.executable, "-c", py_code],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = p.communicate(input=json.dumps({"tool_input": tool_input}))
            return stdout.strip()

        # Case 1: Source code file -> Should return "1"
        res = run_hook_py({"path": "install.py"})
        self.assertEqual(res, "1")

        # Case 2: Skill file -> Should return empty
        res = run_hook_py({"path": "skills/frontend-design/SKILL.md"})
        self.assertEqual(res, "")

        # Case 3: Ignored path -> Should return empty
        res = run_hook_py({"path": "graphify-out/graph.json"})
        self.assertEqual(res, "")

    def test_claude_bash_hook_filtering(self):
        """Test the command-filtering logic in the Claude PreToolUse Bash hook."""
        claude_proj = REPO_DIR / ".claude" / "settings.json"
        with open(claude_proj, "r", encoding="utf-8") as f:
            settings = json.load(f)

        bash_hook = None
        for h in settings["hooks"]["PreToolUse"]:
            if h["matcher"] == "Bash":
                bash_hook = h["hooks"][0]["command"]
                break

        self.assertIsNotNone(bash_hook)

        # Test block commands
        blocked_commands = [
            "grep -rn 'Booking' apps/web/",
            "cat apps/web/proxy.ts",
            "head -n 10 apps/web/proxy.ts",
            "tail apps/web/proxy.ts",
            "wc -l apps/web/proxy.ts",
            "rg 'Booking'",
            "find . -name '*.ts'"
        ]

        for cmd in blocked_commands:
            tool_input = {"command": cmd}
            p = subprocess.Popen(
                bash_hook,
                shell=True,
                cwd=str(REPO_DIR),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = p.communicate(input=json.dumps({"tool_input": tool_input}))
            
            output_data = json.loads(stdout.strip())
            self.assertIn("hookSpecificOutput", output_data)
            self.assertEqual(output_data["hookSpecificOutput"].get("permissionDecision"), "deny")
            self.assertIn("BLOCKED by graphify hook", output_data["hookSpecificOutput"]["permissionDecisionReason"])

        # Test allowed commands
        allowed_commands = [
            "yarn build",
            "echo 'hello'",
            "python3 install.py",
            "rtk graphify query 'project structure' | head -200",
            "graphify query 'main modules' | grep app"
        ]
        for cmd in allowed_commands:
            tool_input = {"command": cmd}
            p = subprocess.Popen(
                bash_hook,
                shell=True,
                cwd=str(REPO_DIR),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = p.communicate(input=json.dumps({"tool_input": tool_input}))
            self.assertEqual(stdout.strip(), "")

    def test_codex_hook_exits_successfully(self):
        """Test that Codex graphify hook check runs successfully."""
        p = subprocess.run(
            ["graphify", "hook-check"],
            capture_output=True,
            text=True
        )
        self.assertEqual(p.returncode, 0)



if __name__ == "__main__":
    unittest.main()
