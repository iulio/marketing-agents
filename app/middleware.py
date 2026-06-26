# app/middleware.py
from fastapi import Request, HTTPException
from typing import Optional
from .auth import verify_token

async def get_current_user(token: str) -> Optional[dict]:
    """Get current user from token."""
    payload = verify_token(token)
    if not payload:
        return None
    return payload

def require_role(allowed_roles: list):
    """Decorator to check if user has required role."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get token from request
            request = kwargs.get('request')
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                raise HTTPException(status_code=401, detail="No request found")
            
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                raise HTTPException(status_code=401, detail="Not authenticated")
            
            token = auth_header.split(' ')[1]
            user = await get_current_user(token)
            if not user:
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            
            if user.get('role') not in allowed_roles:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            
            request.state.user = user
            return await func(*args, **kwargs)
        return wrapper
    return decorator