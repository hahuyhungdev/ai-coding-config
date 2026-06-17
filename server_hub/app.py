import urllib.parse
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .constants import REPO_DIR
from .routes import router
from .utils import is_safe_path

def create_app() -> FastAPI:
    app = FastAPI(title="AI Configuration Web Server")
    
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])
    
    # 2. Custom Security Header Middleware for Cross-Origin Referer / Origin blocks
    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            # Origin check
            origin = request.headers.get("origin")
            if origin:
                parsed = urllib.parse.urlparse(origin)
                if parsed.hostname not in ("localhost", "127.0.0.1"):
                    return Response("Forbidden: Cross-Origin request blocked", status_code=403)
            
            # Referer check
            referer = request.headers.get("referer")
            if referer:
                parsed = urllib.parse.urlparse(referer)
                if parsed.hostname and parsed.hostname not in ("localhost", "127.0.0.1"):
                    return Response("Forbidden: Cross-Origin referer blocked", status_code=403)

            # Content-Type check for POST requests to /api/
            if request.method == "POST" and request.url.path.startswith("/api/"):
                content_type = request.headers.get("content-type", "")
                if not content_type.split(";")[0].strip().lower() == "application/json":
                    return Response(
                        "Unsupported Media Type: Content-Type must be application/json",
                        status_code=415
                    )
                    
            response = await call_next(request)
            return response
            
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 3. Include API endpoints
    app.include_router(router)
    
    # 4. Catch-all for Static files & SPA Routing
    @app.get("/{path:path}")
    def serve_static(request: Request, path: str):
        if not path:
            path = "index.html"
            
        unquoted_path = urllib.parse.unquote(path).strip("/")
        
        # Screenshot/media serving (e.g. Playwright, Gemini logs, Claude logs)
        if any(x in unquoted_path for x in (".playwright-mcp", ".gemini", ".claude", ".codex")):
            file_path = Path("/") / unquoted_path if unquoted_path.startswith("home/") else Path.home() / unquoted_path
            if not file_path.exists():
                file_path = REPO_DIR / unquoted_path

            allowed_bases = [
                REPO_DIR,
                Path.home() / ".gemini",
                Path.home() / ".claude",
                Path.home() / ".codex",
                Path.home() / ".playwright-mcp"
            ]
            if not is_safe_path(file_path, allowed_bases):
                return Response("Forbidden: Path is outside of allowed directories", status_code=403)

            if file_path.exists() and file_path.is_file():
                media_type = "image/png" if file_path.suffix == ".png" else "application/octet-stream"
                return FileResponse(file_path, media_type=media_type)
            else:
                return Response("File not found", status_code=404)

        # Dist serving
        dist_dir = REPO_DIR / "frontend" / "dist"
        file_to_serve = dist_dir / "index.html" if path == "index.html" else dist_dir / path
        
        if dist_dir.exists() and file_to_serve.exists() and file_to_serve.is_file() and dist_dir in file_to_serve.resolve().parents:
            response = FileResponse(file_to_serve)
            if path == "index.html" and getattr(app.state, "session_token", None):
                response.set_cookie(
                    "session_token",
                    app.state.session_token,
                    path="/",
                    httponly=True,
                    samesite="strict"
                )
            return response

        # SPA Routing Fallback
        if not path.startswith("api/") and dist_dir.exists() and (dist_dir / "index.html").exists():
            response = FileResponse(dist_dir / "index.html")
            if getattr(app.state, "session_token", None):
                response.set_cookie(
                    "session_token",
                    app.state.session_token,
                    path="/",
                    httponly=True,
                    samesite="strict"
                )
            return response

        # Repo fallback index
        if path == "index.html" and not dist_dir.exists() and (REPO_DIR / "index.html").exists():
            response = FileResponse(REPO_DIR / "index.html")
            if getattr(app.state, "session_token", None):
                response.set_cookie(
                    "session_token",
                    app.state.session_token,
                    path="/",
                    httponly=True,
                    samesite="strict"
                )
            return response

        return Response("Not Found", status_code=404)
        
    return app
