import os
import sys
import json
import subprocess
import unittest
from pathlib import Path

CAL_DIY_DIR = Path("/home/huyhung/projects/personals/cal.diy")
if not CAL_DIY_DIR.exists():
    CAL_DIY_DIR = Path(__file__).resolve().parent.parent

AI_CFG_DIR = Path(__file__).resolve().parent.parent



class TestCalDiyIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Verify directory exists
        if not CAL_DIY_DIR.exists():
            raise unittest.SkipTest(f"Directory {CAL_DIY_DIR} does not exist")
        
        # Verify graph.json exists
        cls.graph_json = CAL_DIY_DIR / "graphify-out" / "graph.json"
        if not cls.graph_json.exists():
            raise unittest.SkipTest(f"graphify-out/graph.json not built in {CAL_DIY_DIR.name}. Run 'graphify update .' first.")

    def test_claude_bash_hook_grep(self):
        """Verify the Claude Bash hook intercepts grep commands in cal.diy."""
        claude_settings_path = CAL_DIY_DIR / ".claude" / "settings.json"
        self.assertTrue(claude_settings_path.exists())
        
        with open(claude_settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
            
        bash_hook = None
        for item in settings["hooks"]["PreToolUse"]:
            if item["matcher"] == "Bash":
                bash_hook = item["hooks"][0]["command"]
                break
                
        self.assertIsNotNone(bash_hook)
        
        # Test Case: tool_input has a grep command
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
            
            # We run the shell command in CAL_DIY_DIR with the tool_input fed via stdin
            p = subprocess.Popen(
                bash_hook,
                shell=True,
                cwd=str(CAL_DIY_DIR),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = p.communicate(input=json.dumps({"tool_input": tool_input}))
            
            # It should print permissionDecision: deny with graphify instructions
            output_data = json.loads(stdout.strip())
            self.assertIn("hookSpecificOutput", output_data)
            self.assertEqual(output_data["hookSpecificOutput"].get("permissionDecision"), "deny", f"Command failed to block: {cmd}")
            self.assertIn("permissionDecisionReason", output_data["hookSpecificOutput"])
            self.assertIn("BLOCKED by graphify hook", output_data["hookSpecificOutput"]["permissionDecisionReason"])
            self.assertIn("graphify query", output_data["hookSpecificOutput"]["permissionDecisionReason"])

    def test_claude_bash_hook_non_grep(self):
        """Verify the Claude Bash hook does not intercept non-grep commands."""
        claude_settings_path = CAL_DIY_DIR / ".claude" / "settings.json"
        with open(claude_settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
            
        bash_hook = None
        for item in settings["hooks"]["PreToolUse"]:
            if item["matcher"] == "Bash":
                bash_hook = item["hooks"][0]["command"]
                break
                
        # Test Cases: tool_input has non-blocked commands
        allowed_cmds = [
            "yarn build",
            "rtk graphify query 'project structure' | head -200"
        ]
        
        for cmd in allowed_cmds:
            tool_input = {"command": cmd}
            p = subprocess.Popen(
                bash_hook,
                shell=True,
                cwd=str(CAL_DIY_DIR),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = p.communicate(input=json.dumps({"tool_input": tool_input}))
            
            # It should exit silently with empty output
            self.assertEqual(stdout.strip(), "", f"Command was blocked: {cmd}")

    def test_claude_read_hook_src(self):
        """Verify the Claude Read|Glob hook intercepts reading of source files in cal.diy."""
        claude_settings_path = CAL_DIY_DIR / ".claude" / "settings.json"
        with open(claude_settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
            
        read_hook = None
        for item in settings["hooks"]["PreToolUse"]:
            if item["matcher"] == "Read|Glob":
                read_hook = item["hooks"][0]["command"]
                break
                
        self.assertIsNotNone(read_hook)
        
        # Test Case: read a typescript/python file
        file_path = "apps/web/proxy.ts"
        if not (CAL_DIY_DIR / file_path).exists():
            file_path = "install.py"
        tool_input = {"file_path": file_path}
        
        p = subprocess.Popen(
            read_hook,
            shell=True,
            cwd=str(CAL_DIY_DIR),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = p.communicate(input=json.dumps({"tool_input": tool_input}))
        
        # It should block with permissionDecision: deny and suggest using graphify
        output_data = json.loads(stdout.strip())
        self.assertIn("hookSpecificOutput", output_data)
        self.assertEqual(output_data["hookSpecificOutput"].get("permissionDecision"), "deny")
        self.assertIn("permissionDecisionReason", output_data["hookSpecificOutput"])
        self.assertIn("BLOCKED by graphify hook", output_data["hookSpecificOutput"]["permissionDecisionReason"])
        self.assertIn("graphify explain", output_data["hookSpecificOutput"]["permissionDecisionReason"])

    def test_claude_read_hook_ignored(self):
        """Verify the Claude Read|Glob hook ignores non-source or excluded files in cal.diy."""
        claude_settings_path = CAL_DIY_DIR / ".claude" / "settings.json"
        with open(claude_settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
            
        read_hook = None
        for item in settings["hooks"]["PreToolUse"]:
            if item["matcher"] == "Read|Glob":
                read_hook = item["hooks"][0]["command"]
                break
                
        # Test Case: read graph.json itself (ignored path)
        tool_input = {"file_path": "graphify-out/graph.json"}
        
        p = subprocess.Popen(
            read_hook,
            shell=True,
            cwd=str(CAL_DIY_DIR),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = p.communicate(input=json.dumps({"tool_input": tool_input}))
        
        self.assertEqual(stdout.strip(), "")

    def test_gemini_before_tool_hook_src(self):
        """Verify the Gemini BeforeTool hook intercepts source files in cal.diy."""
        gemini_settings_path = CAL_DIY_DIR / ".gemini" / "settings.json"
        self.assertTrue(gemini_settings_path.exists())
        
        with open(gemini_settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
            
        hook_cmd = settings["hooks"]["BeforeTool"][0]["hooks"][0]["command"]
        
        # Test Case: reading a typescript/python file
        file_path = "apps/web/cron-tester.ts"
        if not (CAL_DIY_DIR / file_path).exists():
            file_path = "install.py"
        tool_input = {"file_path": file_path}
        
        p = subprocess.Popen(
            hook_cmd,
            shell=True,
            cwd=str(CAL_DIY_DIR),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = p.communicate(input=json.dumps({"tool_input": tool_input}))
        
        output_data = json.loads(stdout.strip())
        self.assertEqual(output_data.get("decision"), "deny")
        self.assertIn("additionalContext", output_data)
        self.assertIn("BLOCKED by graphify hook", output_data["additionalContext"])
        self.assertIn("graphify explain", output_data["additionalContext"])

    def test_gemini_before_tool_hook_ignored(self):
        """Verify the Gemini BeforeTool hook ignores excluded files in cal.diy."""
        gemini_settings_path = CAL_DIY_DIR / ".gemini" / "settings.json"
        with open(gemini_settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
            
        hook_cmd = settings["hooks"]["BeforeTool"][0]["hooks"][0]["command"]
        
        # Test Case: reading a skill file
        tool_input = {"file_path": "skills/frontend-design/SKILL.md"}
        
        p = subprocess.Popen(
            hook_cmd,
            shell=True,
            cwd=str(CAL_DIY_DIR),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = p.communicate(input=json.dumps({"tool_input": tool_input}))
        
        output_data = json.loads(stdout.strip())
        self.assertEqual(output_data.get("decision"), "allow")
        self.assertNotIn("additionalContext", output_data)


if __name__ == "__main__":
    unittest.main()
