# -*- coding: utf-8 -*-
import sys
import io
import re
import os
import pathlib
from graphify.__main__ import main as original_main

# Monkeypatch graphify to support gemini-cli backend
try:
    import graphify.llm
    from pathlib import Path
    import shutil
    import subprocess
    import json

    # 1. Register gemini-cli backend
    if "gemini-cli" not in graphify.llm.BACKENDS:
        graphify.llm.BACKENDS["gemini-cli"] = {
            "default_model": "gemini-cli-plan",
            "pricing": {"input": 0.0, "output": 0.0},
            "temperature": 0,
            "max_tokens": 16384,
        }
    if hasattr(graphify.llm, "_PATH_IMAGE_BACKENDS"):
        graphify.llm._PATH_IMAGE_BACKENDS.add("gemini-cli")

    # 2. Implement gemini-cli call function
    def _call_gemini_cli(user_message: str, max_tokens: int = 8192, *, deep_mode: bool = False) -> dict:
        agy_cmd = "agy"
        if shutil.which(agy_cmd) is None:
            raise RuntimeError("Antigravity CLI (agy) not found on $PATH")

        cli_args = [agy_cmd, "-p", user_message, "--dangerously-skip-permissions"]
        cli_model = os.environ.get("GRAPHIFY_GEMINI_CLI_MODEL", "").strip()
        if cli_model:
            cli_args.extend(["--model", cli_model])

        proc = subprocess.run(
            cli_args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=600,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"agy -p exited {proc.returncode}: {proc.stderr.strip()[:500]}"
            )

        raw_content = proc.stdout.strip()
        result = graphify.llm._parse_llm_json(raw_content or "{}")
        result["input_tokens"] = 0
        result["output_tokens"] = 0
        result["model"] = cli_model or "gemini-cli-model"
        result["finish_reason"] = "stop"
        return result

    # 3. Patch extract_files_direct
    original_extract_files_direct = graphify.llm.extract_files_direct

    def patched_extract_files_direct(files, backend=None, api_key=None, model=None, root=Path("."), *, deep_mode=False):
        if backend == "gemini-cli":
            text_files, image_files = graphify.llm._partition_semantic_files(files)
            user_msg = graphify.llm._read_files(text_files, root)
            max_out = graphify.llm._resolve_max_tokens(8192)
            return _call_gemini_cli(user_msg, max_tokens=max_out, deep_mode=deep_mode)
        return original_extract_files_direct(files, backend, api_key, model, root, deep_mode=deep_mode)

    graphify.llm.extract_files_direct = patched_extract_files_direct

    # 4. Patch _call_llm
    original_call_llm = graphify.llm._call_llm

    def patched_call_llm(prompt, *, backend, max_tokens=200, model=None):
        if backend == "gemini-cli":
            agy_cmd = "agy"
            if shutil.which(agy_cmd) is None:
                raise RuntimeError("Antigravity CLI (agy) not found on $PATH")
            cli_args = [agy_cmd, "-p", prompt, "--dangerously-skip-permissions"]
            cli_model = os.environ.get("GRAPHIFY_GEMINI_CLI_MODEL", "").strip()
            if cli_model:
                cli_args.extend(["--model", cli_model])
            proc = subprocess.run(
                cli_args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=600,
                check=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"agy -p exited {proc.returncode}: {proc.stderr.strip()[:500]}")
            return proc.stdout.strip()
        return original_call_llm(prompt, backend=backend, max_tokens=max_tokens, model=model)

    graphify.llm._call_llm = patched_call_llm

except Exception as e:
    print(f"[WARN] Failed to monkeypatch gemini-cli support into graphify: {e}", file=sys.stderr)

def is_peripheral(name, src):
    name_l = name.lower()
    src_l = src.lower()
    # Patterns that represent tests, documentation, or minor operational scripts
    patterns = [
        "test", "verify_", "flatten_", "check_", "backfill_", 
        "run_quant", "ops_", "benchmark", "visualize", "setup_cli"
    ]
    return any(p in name_l or p in src_l for p in patterns)

def post_process_output(output):
    if "NODE " not in output:
        return output

    lines = output.splitlines()
    header_lines = []
    node_lines = []
    edge_lines = []
    other_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("NODE "):
            node_lines.append(stripped)
        elif stripped.startswith("EDGE "):
            edge_lines.append(stripped)
        elif stripped.startswith("Traversal:") or stripped.startswith("Node:") or stripped.startswith("Connections:"):
            header_lines.append(line)
        else:
            other_lines.append(line)

    core_nodes = []
    peripheral_nodes = []

    # Parse node properties
    node_pattern = re.compile(r'NODE\s+(.*?)(?:\s+\[src=(.*?)\s+loc=(.*?)\s+community=(.*?)\])?$')

    node_by_name = {}
    for node_line in node_lines:
        match = node_pattern.match(node_line)
        if match:
            name, src, loc, comm = match.groups()
            src = src or ""
            loc = loc or ""
            comm = comm or ""
            
            node_info = {
                "line": node_line,
                "name": name.strip(),
                "src": src.strip(),
                "loc": loc.strip(),
                "community": comm.strip()
            }
            node_by_name[node_info["name"]] = node_info
            
            if is_peripheral(node_info["name"], node_info["src"]):
                peripheral_nodes.append(node_info)
            else:
                core_nodes.append(node_info)
        else:
            core_nodes.append({
                "line": node_line,
                "name": node_line,
                "src": "",
                "loc": "",
                "community": ""
            })

    # Parse edge relationships (focusing on calls)
    edge_pattern = re.compile(r'EDGE\s+(.*?)\s+--calls-->\s+(.*?)$')
    calls_map = {}
    for edge_line in edge_lines:
        match = edge_pattern.match(edge_line)
        if match:
            src, target = match.groups()
            src = src.strip()
            target = target.strip()
            if src not in calls_map:
                calls_map[src] = []
            calls_map[src].append(target)

    # Reconstruct Linear Call Chain
    entrypoints = []
    start_match = re.search(r"Start:\s*\[(.*?)\]", "".join(header_lines))
    if start_match:
        entrypoints = [e.strip("'\" ") for e in start_match.group(1).split(",") if e.strip("'\" ")]
    
    if not entrypoints:
        # Fallback: find nodes in calls_map that are never targets
        targets = set()
        for t_list in calls_map.values():
            targets.update(t_list)
        entrypoints = [src for src in calls_map if src not in targets]

    def get_chain(node, visited, depth=0):
        if depth > 5 or node in visited:
            return []
        visited.add(node)
        chain = [node]
        if node in calls_map:
            for child in calls_map[node]:
                sub_chain = get_chain(child, visited.copy(), depth + 1)
                if sub_chain:
                    chain.append(sub_chain)
        return chain

    def format_chain(chain, indent=""):
        if not chain:
            return ""
        res = ""
        node = chain[0]
        res += f"{indent}↳ {node}\n"
        for child in chain[1:]:
            if isinstance(child, list):
                res += format_chain(child, indent + "  ")
        return res

    linear_chains_str = ""
    if calls_map:
        visited_global = set()
        for ep in entrypoints:
            chain = get_chain(ep, visited_global)
            if chain and len(chain) > 1:
                linear_chains_str += format_chain(chain)

    # Recommended files to read next
    recommendations = []
    pwd = os.getcwd()
    
    def get_node_score(node):
        score = 0
        if node["src"]:
            score += 10
        if node["loc"]:
            score += 5
        if node["name"] in calls_map:
            score += len(calls_map[node["name"]]) * 2
        return score

    sorted_core = sorted(core_nodes, key=get_node_score, reverse=True)
    
    seen_files = set()
    for node in sorted_core:
        if node["src"] and node["src"] not in seen_files:
            file_path = os.path.abspath(os.path.join(pwd, node["src"]))
            # Format line anchor
            loc_num = node["loc"].strip("L")
            loc_suffix = f"#L{loc_num}" if loc_num.isdigit() else ""
            display_name = f"{node['src']}:{node['loc']}" if node["loc"] else node["src"]
            recommendations.append(f"  - [{display_name}](file://{file_path}{loc_suffix}) (Symbol: {node['name']})")
            seen_files.add(node["src"])
            if len(recommendations) >= 5:
                break

    # Reassemble output cleanly
    new_output = []
    new_output.extend(header_lines)
    
    if other_lines:
        new_output.extend(other_lines)
        new_output.append("")

    if linear_chains_str:
        new_output.append("🔗 Linear Call Chain:")
        new_output.append(linear_chains_str.rstrip())
        new_output.append("")

    if recommendations:
        new_output.append("💡 Recommended Files to Read Next:")
        new_output.extend(recommendations)
        new_output.append("")

    new_output.append("📦 Core/Supporting Nodes:")
    for n in core_nodes:
        new_output.append(f"  {n['line']}")
    new_output.append("")

    if peripheral_nodes:
        new_output.append("⚙️ Peripheral Nodes (Tests & Scripts):")
        for n in peripheral_nodes:
            new_output.append(f"  {n['line']}")
        new_output.append("")

    if edge_lines:
        new_output.append("🔌 Edges:")
        new_output.extend(edge_lines)
        new_output.append("")

    return "\n".join(new_output)

def wrapper_main():
    # Detect if query or explain commands are used to apply post-processing
    is_query_cmd = any(arg in sys.argv for arg in ["query", "explain", "path", "affected"])
    
    if not is_query_cmd:
        # Directly pass through to original main without buffering
        sys.exit(original_main())

    # Capture stdout of original main
    stdout_backup = sys.stdout
    captured_stdout = io.StringIO()
    sys.stdout = captured_stdout

    exit_code = 0
    try:
        original_main()
    except SystemExit as e:
        exit_code = e.code if e.code is not None else 0
    except Exception as exc:
        sys.stdout = stdout_backup
        print(f"Error executing Graphify: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        sys.stdout = stdout_backup

    output = captured_stdout.getvalue()
    try:
        processed = post_process_output(output)
        print(processed)
    except Exception as post_exc:
        # Fallback to original output if post-processing fails
        print(output)
        print(f"[WARN] Graphify wrapper post-processing failed: {post_exc}", file=sys.stderr)

    sys.exit(exit_code)

if __name__ == "__main__":
    wrapper_main()
