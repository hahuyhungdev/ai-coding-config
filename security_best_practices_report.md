# Security Best Practices Review & Scan Report

**Project:** `ai-coding-config` / `agy`  
**Date:** June 17, 2026  
**Auditor:** Antigravity AI  

---

## Executive Summary

A comprehensive security scan and codebase audit was performed using Graphify analysis and security best practice guidelines. The scan focused on local HTTP endpoints, subprocess execution, credential storage, path validation, and file permissions.

The review revealed that while standard user permissions are configured for some token writes, the codebase contains major architectural vulnerabilities within the local HTTP server (`server.py` / `server_hub`) and configuration utilities:
- **Two Critical vulnerabilities** regarding unauthenticated command execution and arbitrary sensitive file reads (Local File Inclusion) via local HTTP endpoints.
- **One Medium vulnerability** regarding insecure permission settings on sensitive token and configuration file writes.

---

## Detailed Findings

### SEC-001: Inconsistent File Permissions on Sensitive Token and Configuration Writes (Medium)

- **Severity:** Medium
- **Target Files:** 
  - [tools/agy/switch.py](tools/agy/switch.py#L217-L220) (Lines 217-220, 339-340, 411-413)
  - [server_hub/mcp_manager.py](server_hub/mcp_manager.py#L62-L86) (Lines 62-63, 84-85)

#### Impact Statement
OAuth credentials and configuration files containing system paths and server secrets can be created with world-readable permissions (e.g. `0644`), exposing credentials to other local users on the same machine.

#### Description
While `agy-status.py` sets written tokens to `0600` permissions, `switch.py` and `mcp_manager.py` write OAuth tokens (`antigravity-oauth-token`) and system-wide configuration files (`~/.claude.json`, `~/.gemini/config/mcp_config.json`) using standard `open()` writes. This leaves them vulnerable to default system umask permissions.

#### Recommendation
Enforce strict user-only permissions (`0600`) after writing any credential or configuration payload:
```python
os.chmod(file_path, 0o600)
```

---

### SEC-002: Unauthenticated Arbitrary Command Execution via Local HTTP Endpoint (Critical)

- **Severity:** Critical
- **Target File:** [server_hub/handler.py](server_hub/handler.py#L482-L489)

#### Impact Statement
A local attacker or malicious application can send unauthenticated HTTP POST requests to `/api/simulator/execute` to run arbitrary shell commands on the host under the server user's privileges.

#### Description
The local server runs `/api/simulator/execute` to simulate runs. It takes a raw `CommandLine` string and executes it via `subprocess.run(shell=True)`. The endpoint lacks API key or session validation, and the origin validation check can be bypassed simply by omitting the `Origin` and `Referer` headers from the request.

#### Recommendation
Disable this endpoint in non-developer/production environments. If execution is required, enforce a random API key authentication header and avoid `shell=True` entirely by splitting arguments safely.

---

### SEC-003: Unauthenticated Sensitive File Read / Local File Inclusion (Critical)

- **Severity:** Critical
- **Target File:** [server_hub/handler.py](server_hub/handler.py#L580-L585)

#### Impact Statement
An unauthenticated local attacker or malicious website (via DNS rebinding) can read sensitive credentials like Google OAuth tokens and client databases directly via static HTTP GET routes.

#### Description
In `_serve_static_resources`, the handler checks if a URL path contains sensitive keywords like `".gemini"` or `".claude"`. If it does, it dynamically resolves the path to the user's home directory (`Path.home() / unquoted_path`) and returns the raw file contents (e.g. `/api/.gemini/antigravity-cli/accounts.json`), bypassing all sandbox directory boundaries.

#### Recommendation
Never dynamically resolve file paths from home directories based on substring keywords. Restrict file serving exclusively to a whitelist of public subdirectories (such as `REPO_DIR / "frontend/dist"` or a designated screenshots directory), and strictly validate that resolving files stay within those paths using `os.path.commonpath`.
