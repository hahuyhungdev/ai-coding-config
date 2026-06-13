import json
from pathlib import Path

def map_tool_name_to_step_type(tool_name: str) -> str:
    """Map various tool names from different CLIs to a unified step type."""
    name_lower = tool_name.lower()
    if name_lower in ("bash", "execute_command", "run_command", "run_shell_command"):
        return "RUN_COMMAND"
    elif name_lower in ("read", "view_file", "read_file", "get_file_contents"):
        return "VIEW_FILE"
    elif name_lower in ("grep", "grep_search", "search_code", "search_issues"):
        return "GREP_SEARCH"
    elif name_lower in ("list", "list_directory", "list_dir"):
        return "LIST_DIRECTORY"
    elif name_lower in ("replace_file_content", "write_to_file", "multi_replace_file_content", "apply_patch", "edit_file", "create_or_update_file", "push_files"):
        return "CODE_ACTION"
    elif name_lower in ("search_web", "google_search", "search_repositories"):
        return "SEARCH_WEB"
    elif name_lower in ("read_url_content", "read_url", "read_browser_page"):
        return "READ_URL_CONTENT"
    elif name_lower in ("ask_question", "ask_permission"):
        return "ASK_QUESTION"
    elif name_lower in ("invoke_subagent", "define_subagent"):
        return "INVOKE_SUBAGENT"
    elif name_lower in ("list_resources", "list_permissions"):
        return "LIST_RESOURCES"
    else:
        return "MCP_TOOL"

def parse_gemini_jsonl(log_file: Path) -> list:
    steps = []
    try:
        with log_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    steps.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        pass

    # Post-process to associate tool calls args with execution steps
    pending_tool_calls = []
    for step in steps:
        step_type = step.get("type")
        if step_type == "PLANNER_RESPONSE":
            tool_calls = step.get("tool_calls", [])
            for tc in tool_calls:
                tc_name = tc.get("name")
                tc_args = tc.get("args", {})
                # Clean up string-wrapped arguments if they are double-quoted
                cleaned_args = {}
                if isinstance(tc_args, dict):
                    for k, v in tc_args.items():
                        if isinstance(v, str):
                            v_clean = v.strip()
                            if (v_clean.startswith('"') and v_clean.endswith('"')) or (v_clean.startswith("'") and v_clean.endswith("'")):
                                try:
                                    v_unquoted = json.loads(v_clean)
                                    if isinstance(v_unquoted, str):
                                        v_clean = v_unquoted
                                    else:
                                        v_clean = v_clean[1:-1]
                                except Exception:
                                    v_clean = v_clean[1:-1]
                            cleaned_args[k] = v_clean
                        else:
                            cleaned_args[k] = v
                else:
                    cleaned_args = tc_args
                pending_tool_calls.append({
                    "name": tc_name,
                    "args": cleaned_args
                })
        elif step_type not in ("USER_INPUT", "PLANNER_RESPONSE", "CONVERSATION_HISTORY"):
            # This is a tool execution step. Find the first pending tool call that matches.
            matched_idx = -1
            for i, tc in enumerate(pending_tool_calls):
                mapped_type = map_tool_name_to_step_type(tc["name"])
                if mapped_type == step_type:
                    matched_idx = i
                    break
            
            if matched_idx != -1:
                tc = pending_tool_calls.pop(matched_idx)
                step["resolved_args"] = tc["args"]
                step["name"] = tc["name"]
            elif pending_tool_calls:
                tc = pending_tool_calls.pop(0)
                step["resolved_args"] = tc["args"]
                step["name"] = tc["name"]

    return steps

def parse_claude_jsonl(log_file: Path) -> list:
    steps = []
    tool_calls_map = {}
    try:
        with log_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    line_type = data.get("type")
                    
                    if line_type == "user" and "message" in data:
                        msg = data["message"]
                        role = msg.get("role")
                        if role == "user":
                            content = msg.get("content", "")
                            if isinstance(content, list):
                                for block in content:
                                    if block.get("type") == "tool_result":
                                        tool_id = block.get("tool_use_id")
                                        stdout = block.get("content", "")
                                        if isinstance(stdout, list):
                                            stdout_parts = []
                                            for b in stdout:
                                                if isinstance(b, dict) and b.get("type") == "text":
                                                    stdout_parts.append(b.get("text", ""))
                                                elif isinstance(b, str):
                                                    stdout_parts.append(b)
                                            stdout = "\n".join(stdout_parts)
                                        elif not isinstance(stdout, str):
                                            stdout = str(stdout)
                                        is_error = block.get("is_error", False)
                                        
                                        if tool_id in tool_calls_map:
                                            t_call = tool_calls_map[tool_id]
                                            steps.append({
                                                "type": map_tool_name_to_step_type(t_call["name"]),
                                                "name": t_call["name"],
                                                "content": stdout,
                                                "status": "ERROR" if is_error else "OK",
                                                "resolved_args": t_call["input"]
                                            })
                            else:
                                steps.append({
                                    "type": "USER_INPUT",
                                    "content": content
                                })
                                
                    elif line_type == "assistant" and "message" in data:
                        msg = data["message"]
                        role = msg.get("role")
                        if role == "assistant":
                            blocks = msg.get("content", [])
                            text_content = []
                            thinking_content = []
                            proposed_tool_calls = []
                            
                            for block in blocks:
                                b_type = block.get("type")
                                if b_type == "text":
                                    text_content.append(block.get("text", ""))
                                elif b_type == "thinking":
                                    thinking_content.append(block.get("thinking", ""))
                                elif b_type == "tool_use":
                                    t_id = block.get("id")
                                    t_name = block.get("name")
                                    t_input = block.get("input", {})
                                    
                                    tool_calls_map[t_id] = {
                                        "name": t_name,
                                        "input": t_input
                                    }
                                    proposed_tool_calls.append({
                                        "name": t_name,
                                        "arguments": t_input
                                    })
                                    
                            steps.append({
                                "type": "PLANNER_RESPONSE",
                                "content": "\n".join(text_content),
                                "thinking": "\n".join(thinking_content),
                                "tool_calls": proposed_tool_calls
                            })
                except Exception:
                    continue
    except Exception:
        pass
    return steps

def parse_codex_jsonl(log_file: Path) -> list:
    steps = []
    tool_calls_map = {}
    try:
        with log_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    line_type = data.get("type")
                    
                    if line_type == "response_item" and "payload" in data:
                        payload = data["payload"]
                        payload_type = payload.get("type")
                        
                        if payload_type == "message":
                            role = payload.get("role")
                            content = payload.get("content", [])
                            
                            if role == "user":
                                text_parts = []
                                for block in content:
                                    if isinstance(block, dict):
                                        b_type = block.get("type")
                                        if b_type in ("input_text", "text"):
                                            text_parts.append(block.get("text", ""))
                                    elif isinstance(block, str):
                                        text_parts.append(block)
                                content_str = "\n".join(text_parts).strip()
                                if content_str:
                                    steps.append({
                                        "type": "USER_INPUT",
                                        "content": content_str
                                    })
                                    
                            elif role == "assistant":
                                text_content = []
                                thinking_content = []
                                proposed_tool_calls = []
                                
                                for block in content:
                                    if isinstance(block, dict):
                                        b_type = block.get("type")
                                        if b_type in ("text", "output_text"):
                                            text_content.append(block.get("text", ""))
                                        elif b_type == "thinking":
                                            thinking_content.append(block.get("thinking", ""))
                                    elif isinstance(block, str):
                                        text_content.append(block)
                                        
                                steps.append({
                                    "type": "PLANNER_RESPONSE",
                                    "content": "\n".join(text_content),
                                    "thinking": "\n".join(thinking_content),
                                    "tool_calls": proposed_tool_calls
                                })
                                
                        elif payload_type == "custom_tool_call":
                            call_id = payload.get("call_id")
                            name = payload.get("name")
                            t_input = payload.get("input", "")
                            tool_calls_map[call_id] = {
                                "name": name,
                                "input": t_input
                            }
                            
                        elif payload_type == "custom_tool_call_output":
                            call_id = payload.get("call_id")
                            output_blocks = payload.get("output", [])
                            
                            stdout_parts = []
                            if isinstance(output_blocks, list):
                                for block in output_blocks:
                                    if isinstance(block, dict):
                                        b_type = block.get("type")
                                        if b_type in ("input_text", "text"):
                                            stdout_parts.append(block.get("text", ""))
                                    elif isinstance(block, str):
                                        stdout_parts.append(block)
                            elif isinstance(output_blocks, str):
                                stdout_parts.append(output_blocks)
                                
                            stdout = "\n".join(stdout_parts)
                            is_error = payload.get("is_error", False)
                            
                            if call_id in tool_calls_map:
                                t_call = tool_calls_map[call_id]
                                resolved_args = t_call["input"]
                                if isinstance(resolved_args, str):
                                    resolved_args = {"script": resolved_args}
                                steps.append({
                                    "type": map_tool_name_to_step_type(t_call["name"]),
                                    "name": t_call["name"],
                                    "content": stdout,
                                    "status": "ERROR" if is_error else "OK",
                                    "resolved_args": resolved_args
                                })
                except Exception:
                    continue
    except Exception:
        pass
    return steps
