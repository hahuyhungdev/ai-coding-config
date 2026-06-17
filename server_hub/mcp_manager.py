import os
import json
import re
from pathlib import Path
from .constants import REPO_DIR, SHARED_DISABLED

def get_all_mcp_servers() -> list[str]:
    defaults_path = REPO_DIR / "scripts" / "update-mcp-config.js"
    if defaults_path.exists():
        content = defaults_path.read_text()
        block = re.search(r'defaultServers\s*=\s*\{(.+?)\n\s*\};', content, re.DOTALL)
        if block:
            matches = re.findall(r'(?:\"([^\"]+)\"|\'([^\']+)\'|(\w[\w-]*))\s*:\s*\{', block.group(1))
            servers = [m[0] or m[1] or m[2] for m in matches]
            if servers:
                return servers
    return ["playwright", "context7", "memory", "sequential-thinking", "postgres", "sqlite", "docker", "aws"]

def load_disabled() -> list[str]:
    try:
        with open(SHARED_DISABLED) as f:
            return json.load(f).get("disabledMcpServers", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_disabled(disabled: list[str]) -> None:
    with open(SHARED_DISABLED, "w") as f:
        json.dump({"disabledMcpServers": sorted(disabled)}, f, indent=2)
        f.write("\n")

def get_mcp_servers() -> dict:
    try:
        with open(Path.home() / ".claude.json") as f:
            data = json.load(f)
            configs = {}
            configs.update(data.get("disabledMcpServers", {}))
            configs.update(data.get("mcpServers", {}))
            return configs
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_mcp_configs(updated_configs: dict, disabled_list: list[str]) -> None:
    # 1. Save to Claude config (~/.claude.json)
    claude_json_path = Path.home() / ".claude.json"
    try:
        data = {}
        if claude_json_path.exists():
            with open(claude_json_path) as f:
                data = json.load(f)
        
        mcp_servers = {}
        disabled_mcp_servers = {}
        
        for name, config in updated_configs.items():
            if name in disabled_list:
                disabled_mcp_servers[name] = config
            else:
                mcp_servers[name] = config
                
        data["mcpServers"] = mcp_servers
        data["disabledMcpServers"] = disabled_mcp_servers
        
        with open(claude_json_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        if os.name == 'posix':
            try:
                os.chmod(claude_json_path, 0o600)
            except OSError:
                pass
    except Exception as e:
        print(f"Error saving Claude MCP configs: {e}")

    # 2. Save to Gemini config (~/.gemini/config/mcp_config.json)
    gemini_json_path = Path.home() / ".gemini" / "config" / "mcp_config.json"
    try:
        data = {}
        if gemini_json_path.exists():
            with open(gemini_json_path) as f:
                data = json.load(f)
        
        mcp_servers = {}
        for name, config in updated_configs.items():
            if name not in disabled_list:
                mcp_servers[name] = config
                
        data["mcpServers"] = mcp_servers
        
        gemini_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(gemini_json_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        if os.name == 'posix':
            try:
                os.chmod(gemini_json_path, 0o600)
            except OSError:
                pass
    except Exception as e:
        print(f"Error saving Gemini MCP configs: {e}")

    # 3. Save to Codex config (~/.codex/config.toml)
    codex_toml_path = Path.home() / ".codex" / "config.toml"
    try:
        if codex_toml_path.exists():
            content = codex_toml_path.read_text(encoding="utf-8")
            
            # Remove all existing [mcp_servers.*] blocks and clean up whitespace
            pattern = r'(?m)^\[mcp_servers\.[^\]]+\]\n(?:[^\[\n].*\n| *\n)*'
            content = re.sub(pattern, "", content)
            content = re.sub(r'\n{3,}', '\n\n', content)
            content = content.rstrip() + "\n\n"
            
            # Append active/enabled MCP servers
            for name, config in updated_configs.items():
                if name not in disabled_list:
                    content += f"[mcp_servers.{name}]\n"
                    if "type" in config:
                        content += f'type = "{config["type"]}"\n'
                    if "url" in config:
                        content += f'url = "{config["url"]}"\n'
                    if "command" in config:
                        content += f'command = "{config["command"]}"\n'
                    if "args" in config:
                        args_str = ", ".join(f'"{a}"' for a in config["args"])
                        content += f"args = [{args_str}]\n"
                    if "env" in config and config["env"]:
                        content += f"env = {json.dumps(config['env'])}\n"
                    
                    tools = config.get("tools", {})
                    for tool_name, tool_config in tools.items():
                        content += f"\n[mcp_servers.{name}.tools.{tool_name}]\n"
                        for tk, tv in tool_config.items():
                            if isinstance(tv, bool):
                                content += f"{tk} = {str(tv).lower()}\n"
                            else:
                                content += f'{tk} = "{tv}"\n'
                    content += "\n"
            
            codex_toml_path.write_text(content, encoding="utf-8")
            if os.name == 'posix':
                try:
                    os.chmod(codex_toml_path, 0o600)
                except OSError:
                    pass
    except Exception as e:
        print(f"Error saving Codex MCP configs: {e}")
