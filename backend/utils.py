from pathlib import Path
from fastapi import Header, Cookie, HTTPException, Request, status

def is_safe_path(requested_path, allowed_bases):
    try:
        resolved_path = Path(requested_path).resolve()
        for base in allowed_bases:
            resolved_base = Path(base).resolve()
            if resolved_base in resolved_path.parents or resolved_base == resolved_path:
                return True
        return False
    except Exception:
        return False

def verify_session_token(
    request: Request,
    x_session_token: str | None = Header(default=None, alias="X-Session-Token"),
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None)
):
    # If no session token is configured, skip verification
    expected_token = getattr(request.app.state, "session_token", None)
    if not expected_token:
        return
        
    if x_session_token == expected_token:
        return
        
    if authorization and authorization.startswith("Bearer "):
        bearer_token = authorization[7:].strip()
        if bearer_token == expected_token:
            return
            
    if session_token == expected_token:
        return
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: Invalid or missing session token"
    )
