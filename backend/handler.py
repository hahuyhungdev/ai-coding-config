from http.server import BaseHTTPRequestHandler
from .utils import is_safe_path

# Compatibility wrapper class for standard library HTTP handler
class ConfigHandler(BaseHTTPRequestHandler):
    session_token = None

    def log_message(self, format, *args):
        pass

    @staticmethod
    def handle_get_conversation(handler, conv_id):
        clean_id = "".join(c for c in conv_id if c.isalnum() or c in "-_")
        parts = clean_id.split("__")
        if len(parts) < 2:
            handler.send_error_json(400, "Invalid conversation ID format")
            return
            
        source = parts[0]
        if source not in ("gemini", "claude", "codex"):
            handler.send_error_json(400, f"Unsupported conversation source: {source}")
            return
            
        if source == "claude" and len(parts) < 3:
            handler.send_error_json(400, "Invalid Claude conversation ID format")
            return
            
        if source == "codex":
            if len(parts) < 3:
                handler.send_error_json(400, "Invalid Codex conversation ID format")
                return
            year_month_day = parts[1]
            if len(year_month_day.split("-")) != 3:
                handler.send_error_json(400, "Invalid Codex date format")
                return

        from .metadata import resolve_conversation_log, describe_gemini_transcript_source
        from .parsers import parse_gemini_jsonl, parse_claude_jsonl, parse_codex_jsonl
        from .token_estimator import calculate_session_stats
        import json

        log_file, model_name = resolve_conversation_log(conv_id)
        if log_file is None or not log_file.exists():
            source_cap = source.capitalize() if source != "gemini" else "Gemini"
            handler.send_error_json(404, f"{source_cap} conversation log not found")
            return
            
        steps = []
        log_source = None
        
        if source == "gemini":
            log_source = describe_gemini_transcript_source(parts[1])
            steps = parse_gemini_jsonl(log_file)
        elif source == "claude":
            steps = parse_claude_jsonl(log_file)
        elif source == "codex":
            steps = parse_codex_jsonl(log_file)

        stats = calculate_session_stats(steps, model_name)
        
        payload = {
            "id": clean_id,
            "stats": stats,
            "steps": steps
        }
        if log_source is not None:
            payload["log_source"] = log_source
            
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps(payload).encode("utf-8"))
