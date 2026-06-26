# app/auth.py
import uuid
import jwt
import os
from datetime import datetime, timedelta
from typing import Optional, Dict

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

from .storage import get_user_by_email, verify_user, create_user, get_all_users

def generate_token(user_id: str, email: str, role: str, client_id: Optional[str] = None) -> str:
    """Generate a JWT token for the user."""
    expiration = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "client_id": client_id,
        "exp": expiration,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Optional[Dict]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        print("[Auth] Token expired")
        return None
    except jwt.InvalidTokenError:
        print("[Auth] Invalid token")
        return None

def hash_password(password: str) -> str:
    """Hash a password."""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest() == hashed

def create_default_admin():
    """Create a default admin user if none exists."""
    users = get_all_users()
    if not users:
        print("[Auth] Creating default admin user...")
        create_user({
            "email": "admin@agency.com",
            "password": "admin123",
            "full_name": "Agency Admin",
            "role": "admin",
            "client_id": None
        })
        print("[Auth] Default admin created: admin@agency.com / admin123")