#!/usr/bin/env python3
"""
E2E tests for Graphify Git Hooks integration.
Verifies that post-commit and post-checkout hooks execute successfully
and trigger graph updates as expected in a git repository.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

class TestE2EGitHooks(unittest.TestCase):
    """End-to-End git hooks execution tests."""

    def setUp(self):
        # Create a temp directory for git repository
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)
        
        # Initialize Git repo
        self._run_git(["init", "-b", "master"])
        self._run_git(["config", "user.name", "Test User"])
        self._run_git(["config", "user.email", "test@example.com"])
        
        # Create a dummy python file
        self.src_file = self.repo_path / "app.py"
        self.src_file.write_text("def hello():\n    print('Hello World')\n")
        
        # Initial commit
        self._run_git(["add", "app.py"])
        self._run_git(["commit", "-m", "Initial commit"])

    def tearDown(self):
        # Git hook background processes may hold file locks or be writing to temp dir.
        # Retry cleanup with a short delay to let processes finish.
        for attempt in range(5):
            try:
                self.temp_dir.cleanup()
                return
            except (PermissionError, OSError):
                if attempt < 4:
                    time.sleep(0.5)
                else:
                    raise

    def _run_git(self, args: list[str]) -> str:
        res = subprocess.run(
            ["git"] + args,
            cwd=str(self.repo_path),
            capture_output=True,
            text=True,
            check=True
        )
        return res.stdout

    def test_post_commit_hook_updates_graph(self):
        """Test that post-commit hook successfully updates the graphify index."""
        # 1. Initialize graphify in repository
        subprocess.run(
            ["graphify", "update", "."],
            cwd=str(self.repo_path),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        graph_json = self.repo_path / "graphify-out" / "graph.json"
        self.assertTrue(graph_json.exists())
        
        # Record initial modification time
        initial_mtime = graph_json.stat().st_mtime
        
        # 2. Install hooks
        subprocess.run(
            ["graphify", "hook", "install"],
            cwd=str(self.repo_path),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Verify hook files exist
        post_commit_hook = self.repo_path / ".git" / "hooks" / "post-commit"
        self.assertTrue(post_commit_hook.exists())
        
        # 3. Modify code file and commit to trigger post-commit hook
        self.src_file.write_text("def hello():\n    print('Hello World')\n\ndef new_func():\n    pass\n")
        self._run_git(["add", "app.py"])
        self._run_git(["commit", "-m", "Add new_func"])
        
        # Hook runs in background, so wait up to 5 seconds for graph update
        import time
        updated = False
        for _ in range(50):
            if graph_json.stat().st_mtime > initial_mtime:
                updated = True
                break
            time.sleep(0.1)
            
        self.assertTrue(updated, "graphify graph was not updated by post-commit hook")
        
        # Check if the new function node exists in the graph
        with open(graph_json, "r") as f:
            graph_data = f.read()
        self.assertIn("new_func", graph_data)

    def test_post_checkout_hook_runs(self):
        """Test that post-checkout hook successfully updates the graphify index after checkout."""
        # 1. Create a new branch, modify a file, and commit to create a diff
        self._run_git(["checkout", "-b", "diff-branch"])
        self.src_file.write_text("def hello():\n    print('Hello World')\n\ndef branch_func():\n    pass\n")
        self._run_git(["add", "app.py"])
        self._run_git(["commit", "-m", "Add branch_func on diff-branch"])
        
        # Switch back to master
        self._run_git(["checkout", "master"])

        # 2. Initialize graphify in repository
        subprocess.run(
            ["graphify", "update", "."],
            cwd=str(self.repo_path),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        graph_json = self.repo_path / "graphify-out" / "graph.json"
        self.assertTrue(graph_json.exists())
        
        # 3. Install hooks
        subprocess.run(
            ["graphify", "hook", "install"],
            cwd=str(self.repo_path),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Verify checkout hook exists
        post_checkout_hook = self.repo_path / ".git" / "hooks" / "post-checkout"
        self.assertTrue(post_checkout_hook.exists())
        
        # Record initial modification time
        initial_mtime = graph_json.stat().st_mtime
        
        # 4. Checkout the branch with changes to trigger post-checkout hook
        self._run_git(["checkout", "diff-branch"])
        
        # Wait up to 5 seconds for graph update
        import time
        updated = False
        for _ in range(50):
            if graph_json.stat().st_mtime > initial_mtime:
                updated = True
                break
            time.sleep(0.1)
            
        self.assertTrue(updated, "graphify graph was not updated by post-checkout hook")

if __name__ == "__main__":
    unittest.main()
