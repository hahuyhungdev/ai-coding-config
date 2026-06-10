import sys
import unittest
import urllib.request
import json
import threading
import time
from pathlib import Path
from http.server import ThreadingHTTPServer

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

from server import ConfigHandler, get_all_conversations

class TestConversationsAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Find a free port
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', 0))
        cls.port = s.getsockname()[1]
        s.close()

        # Start the server in a daemon thread
        cls.server = ThreadingHTTPServer(('127.0.0.1', cls.port), ConfigHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        # Give it a moment to start
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
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

if __name__ == "__main__":
    unittest.main()
