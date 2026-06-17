#!/usr/bin/env python3
import sys
import json
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python update_mcp_config.py <config-json-path>", file=sys.stderr)
        sys.exit(1)

    config_file = Path(sys.argv[1])

    # Read shared disabled list
    shared_disabled_path = Path(__file__).resolve().parent.parent / "shared-disabled-mcp.json"
    shared_disabled = []
    if shared_disabled_path.exists():
        try:
            shared = json.loads(shared_disabled_path.read_text(encoding="utf-8"))
            shared_disabled = shared.get("disabledMcpServers", [])
        except Exception:
            pass

    try:
        data = {}
        if config_file.exists():
            content = config_file.read_text(encoding="utf-8").strip()
            if content:
                data = json.loads(content)
        
        if "mcpServers" not in data:
            data["mcpServers"] = {}

        default_servers = {
            "playwright": {
                "command": "npx",
                "args": ["-y", "@playwright/mcp@latest", "--browser", "msedge", "--headless", "--ignore-https-errors", "--isolated", "--output-dir", ".playwright-mcp"]
            },
            "context7": {
                "type": "sse",
                "url": "https://mcp.context7.com/mcp"
            },
            "memory": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-memory"]
            },
            "sequential-thinking": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
            },
            "postgres": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/postgres"]
            },
            "sqlite": {
                "command": "npx",
                "args": ["-y", "mcp-server-sqlite", "--db", "database.db"]
            },
            "docker": {
                "command": "npx",
                "args": ["-y", "mcp-server-docker"]
            },
            "aws": {
                "command": "uvx",
                "args": ["awslabs.aws-api-mcp-server@latest"]
            }
        }

        disabled_obj = data.get("disabledMcpServers", {})
        disabled = set(list(disabled_obj.keys()) + shared_disabled)

        updated = False

        # Remove servers that are now disabled
        for name in disabled:
            if name in data["mcpServers"]:
                del data["mcpServers"][name]
                print(f"Removed disabled server: {name} from {config_file}")
                updated = True

        # Add or update default servers (skip disabled ones)
        for name, config in default_servers.items():
            if name in disabled:
                continue

            if name not in data["mcpServers"]:
                data["mcpServers"][name] = config
                print(f"Initialized {name} MCP in {config_file}")
                updated = True
            else:
                if name == "playwright":
                    # Check playwright configuration details
                    args = data["mcpServers"]["playwright"].get("args", [])
                    p_updated = False
                    if "--isolated" not in args:
                        args.append("--isolated")
                        p_updated = True
                    
                    try:
                        b_idx = args.index("--browser")
                        if b_idx + 1 < len(args) and args[b_idx + 1] != "msedge":
                            args[b_idx + 1] = "msedge"
                            p_updated = True
                    except ValueError:
                        pass

                    try:
                        o_idx = args.index("--output-dir")
                        if o_idx + 1 < len(args) and args[o_idx + 1] != ".playwright-mcp":
                            args[o_idx + 1] = ".playwright-mcp"
                            p_updated = True
                    except ValueError:
                        args.extend(["--output-dir", ".playwright-mcp"])
                        p_updated = True

                    if p_updated:
                        data["mcpServers"]["playwright"]["args"] = args
                        print(f"Updated playwright MCP in {config_file}")
                        updated = True

        if updated:
            config_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    except Exception as e:
        print(f"Error updating {config_file}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
