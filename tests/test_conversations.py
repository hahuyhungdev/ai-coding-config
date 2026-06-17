import sys
import unittest
import urllib.request
import json
import threading
import time
import tempfile
import importlib.util
from pathlib import Path
from http.server import ThreadingHTTPServer

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

from server import app, get_all_conversations
from server_hub.metadata import describe_gemini_transcript_source, resolve_gemini_transcript_path

INSPECT_CONVERSATION_SCRIPT = REPO_DIR / "scripts" / "inspect_conversation.py"
inspect_spec = importlib.util.spec_from_file_location("inspect_conversation", INSPECT_CONVERSATION_SCRIPT)
inspect_conversation = importlib.util.module_from_spec(inspect_spec)
inspect_spec.loader.exec_module(inspect_conversation)

class TestConversationsAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Find a free port
        import socket
        import uvicorn
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', 0))
        cls.port = s.getsockname()[1]
        s.close()

        # Start the server in a daemon thread using uvicorn
        config = uvicorn.Config(app, host='127.0.0.1', port=cls.port, log_level='error')
        cls.server = uvicorn.Server(config)
        cls.server_thread = threading.Thread(target=cls.server.run)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        # Give it a moment to start
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.server_thread.join()

    def test_list_conversations_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/api/conversations"
        try:
            with urllib.request.urlopen(url) as response:
                self.assertEqual(response.status, 200)
                data = json.loads(response.read().decode('utf-8'))
                self.assertIsInstance(data, list)
        except Exception as e:
            self.fail(f"Failed to fetch conversations: {e}")

    def test_get_conversation_not_found(self):
        url = f"http://127.0.0.1:{self.port}/api/conversation/gemini__non_existent_id_123456"
        try:
            with urllib.request.urlopen(url) as response:
                self.fail("Should have returned 404/500 for non-existent conversation")
        except urllib.error.HTTPError as e:
            self.assertIn(e.code, (404, 500))

    def test_gemini_transcript_prefers_full_log_when_available(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            brain_dir = Path(tmp_dir)
            log_dir = brain_dir / "session-123" / ".system_generated" / "logs"
            log_dir.mkdir(parents=True)
            (log_dir / "transcript.jsonl").write_text("truncated\n", encoding="utf-8")
            (log_dir / "transcript_full.jsonl").write_text("full\n", encoding="utf-8")

            resolved = resolve_gemini_transcript_path("session-123", brain_dir=brain_dir)

            self.assertEqual(resolved, log_dir / "transcript_full.jsonl")

    def test_gemini_transcript_falls_back_to_compact_log(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            brain_dir = Path(tmp_dir)
            log_dir = brain_dir / "session-123" / ".system_generated" / "logs"
            log_dir.mkdir(parents=True)
            (log_dir / "transcript.jsonl").write_text("compact\n", encoding="utf-8")

            resolved = resolve_gemini_transcript_path("session-123", brain_dir=brain_dir)

            self.assertEqual(resolved, log_dir / "transcript.jsonl")

    def test_gemini_transcript_source_reports_relative_full_log(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            brain_dir = Path(tmp_dir)
            log_dir = brain_dir / "session-123" / ".system_generated" / "logs"
            log_dir.mkdir(parents=True)
            (log_dir / "transcript_full.jsonl").write_text("full\n", encoding="utf-8")

            source = describe_gemini_transcript_source("session-123", brain_dir=brain_dir)

            self.assertEqual(source["kind"], "full")
            self.assertEqual(source["filename"], "transcript_full.jsonl")
            self.assertEqual(source["relative_path"], "session-123/.system_generated/logs/transcript_full.jsonl")
            self.assertFalse(source["relative_path"].startswith("/"))

    def test_inspect_conversation_script_reports_step_and_keyword(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            brain_dir = Path(tmp_dir)
            log_dir = brain_dir / "session-123" / ".system_generated" / "logs"
            log_dir.mkdir(parents=True)
            (log_dir / "transcript_full.jsonl").write_text(
                json.dumps({"type": "USER_INPUT", "content": "hello"}) + "\n"
                + json.dumps({"type": "PLANNER_RESPONSE", "content": "131 tests passed successfully"}) + "\n",
                encoding="utf-8",
            )

            result = inspect_conversation.inspect_conversation(
                "gemini__session-123",
                brain_dir=brain_dir,
                step_index=1,
                keyword="131 tests passed",
            )

            self.assertEqual(result["log_source"]["kind"], "full")
            self.assertEqual(result["total_steps"], 2)
            self.assertEqual(result["step"]["index"], 1)
            self.assertEqual(result["step"]["type"], "PLANNER_RESPONSE")
            self.assertTrue(result["keyword"]["found"])

    def test_inspect_claude_conversation_script(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            claude_dir = Path(tmp_dir)
            log_dir = claude_dir / "my-project"
            log_dir.mkdir(parents=True)
            (log_dir / "session-abc.jsonl").write_text(
                json.dumps({"type": "user", "message": {"role": "user", "content": "hello claude"}}) + "\n"
                + json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "how can I help"}]}}) + "\n",
                encoding="utf-8"
            )
            
            result = inspect_conversation.inspect_conversation(
                "claude__my-project__session-abc",
                claude_dir=claude_dir,
                step_index=0,
                keyword="hello"
            )
            
            self.assertEqual(result["source"], "claude")
            self.assertEqual(result["total_steps"], 2)
            self.assertEqual(result["step"]["index"], 0)
            self.assertEqual(result["step"]["type"], "USER_INPUT")
            self.assertTrue(result["keyword"]["found"])

    def test_inspect_codex_conversation_script(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            codex_dir = Path(tmp_dir)
            log_dir = codex_dir / "2026" / "06" / "17"
            log_dir.mkdir(parents=True)
            (log_dir / "rollout-xyz.jsonl").write_text(
                json.dumps({"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "text", "text": "run codex"}]}}) + "\n",
                encoding="utf-8"
            )
            
            result = inspect_conversation.inspect_conversation(
                "codex__2026-06-17__rollout-xyz",
                codex_dir=codex_dir,
                step_index=0,
                keyword="codex"
            )
            
            self.assertEqual(result["source"], "codex")
            self.assertEqual(result["total_steps"], 1)
            self.assertEqual(result["step"]["index"], 0)
            self.assertEqual(result["step"]["type"], "USER_INPUT")
            self.assertTrue(result["keyword"]["found"])

    def test_inspect_conversation_compares_compact_and_full_logs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            brain_dir = Path(tmp_dir)
            log_dir = brain_dir / "session-123" / ".system_generated" / "logs"
            log_dir.mkdir(parents=True)
            (log_dir / "transcript.jsonl").write_text(
                json.dumps({"type": "USER_INPUT", "content": "hello"}) + "\n"
                + json.dumps({"type": "PLANNER_RESPONSE", "content": "short compact text"}) + "\n",
                encoding="utf-8",
            )
            (log_dir / "transcript_full.jsonl").write_text(
                json.dumps({"type": "USER_INPUT", "content": "hello"}) + "\n"
                + json.dumps({"type": "PLANNER_RESPONSE", "content": "long full text with compact keyword"}) + "\n",
                encoding="utf-8",
            )

            result = inspect_conversation.inspect_conversation(
                "gemini__session-123",
                brain_dir=brain_dir,
                step_index=1,
                keyword="compact",
                compare_logs=True,
            )

            comparison = result["log_comparison"]
            self.assertTrue(comparison["compact"]["exists"])
            self.assertTrue(comparison["full"]["exists"])
            self.assertEqual(comparison["compact"]["total_steps"], 2)
            self.assertEqual(comparison["full"]["total_steps"], 2)
            self.assertFalse(comparison["step"]["same_content"])
            self.assertEqual(comparison["step"]["compact"]["content_length"], len("short compact text"))
            self.assertEqual(comparison["step"]["full"]["content_length"], len("long full text with compact keyword"))

    def test_invalid_host_header_blocked(self):
        url = f"http://127.0.0.1:{self.port}/api/conversations"
        req = urllib.request.Request(url)
        req.add_header("Host", "attacker.com")
        try:
            urllib.request.urlopen(req)
            self.fail("Should have blocked invalid Host header")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    def test_cross_origin_referer_blocked(self):
        url = f"http://127.0.0.1:{self.port}/api/mcp/test"
        req = urllib.request.Request(
            url, 
            method="POST", 
            data=json.dumps({"command": "node"}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        req.add_header("Referer", "http://attacker.com")
        try:
            urllib.request.urlopen(req)
            self.fail("Should have blocked cross-origin Referer")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 403)

    def test_invalid_content_type_post_blocked(self):
        url = f"http://127.0.0.1:{self.port}/api/mcp/test"
        req = urllib.request.Request(
            url, 
            method="POST", 
            data=json.dumps({"command": "node"}).encode("utf-8"),
            headers={"Content-Type": "text/plain"}
        )
        try:
            urllib.request.urlopen(req)
            self.fail("Should have blocked non-JSON POST requests")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 415)

if __name__ == "__main__":
    unittest.main()
