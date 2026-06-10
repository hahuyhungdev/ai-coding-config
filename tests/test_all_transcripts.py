import sys
from pathlib import Path
import json

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

from server import get_all_conversations, ConfigHandler, parse_gemini_jsonl, parse_claude_jsonl, parse_codex_jsonl

def test_all():
    print("Fetching all conversations...")
    conversations = get_all_conversations()
    print(f"Found {len(conversations)} conversations in total.")
    
    success_count = 0
    failure_count = 0
    
    # Mock ConfigHandler subclass/instance to run handle_get_conversation
    class MockHandler:
        def __init__(self):
            self.response_code = None
            self.headers = {}
            self.response_body = None
            
        def send_response(self, code):
            self.response_code = code
            
        def send_header(self, k, v):
            self.headers[k] = v
            
        def end_headers(self):
            pass
            
        def send_error_json(self, code, msg):
            self.response_code = code
            self.response_body = json.dumps({"error": msg})
            
        def write_response(self, b):
            self.response_body = b.decode('utf-8')
            
    # Mock writing to wfile
    class MockWFile:
        def __init__(self, handler):
            self.handler = handler
        def write(self, b):
            self.handler.write_response(b)

    for conv in conversations:
        conv_id = conv['id']
        source = conv['source']
        print(f"Testing [{source}] {conv_id}...")
        
        handler = MockHandler()
        handler.wfile = MockWFile(handler)
        
        try:
            ConfigHandler.handle_get_conversation(handler, conv_id)
            if handler.response_code == 200:
                # Validate response structure
                data = json.loads(handler.response_body)
                assert 'id' in data
                assert 'stats' in data
                assert 'steps' in data
                
                steps = data['steps']
                # Check each step content type
                for i, step in enumerate(steps):
                    content = step.get('content')
                    assert isinstance(content, str), f"Step {i} content is type {type(content)}, expected string"
                    
                success_count += 1
            else:
                print(f"  FAILED to parse {conv_id}: HTTP {handler.response_code}. Body: {handler.response_body}")
                failure_count += 1
        except Exception as e:
            print(f"  CRASHED testing {conv_id}: {e}")
            import traceback
            traceback.print_exc()
            failure_count += 1
            
    print("\n=== Test Results ===")
    print(f"Total tested: {len(conversations)}")
    print(f"Success:      {success_count}")
    print(f"Failure:      {failure_count}")
    
    if failure_count > 0:
        sys.exit(1)
    else:
        print("All transcripts parsed perfectly without errors!")

if __name__ == "__main__":
    test_all()
