import hashlib
import hmac
import os

try:
    import bcrypt
    _HAS_BCRYPT = True
except ImportError:
    _HAS_BCRYPT = False

import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from app.config import settings

def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt (or standard PBKDF2-SHA256 fallback)."""
    if _HAS_BCRYPT:
        pwd_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")
    else:
        salt = os.urandom(16).hex()
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return f"pbkdf2${salt}${key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against bcrypt or PBKDF2 hash."""
    try:
        if hashed_password.startswith("pbkdf2$"):
            parts = hashed_password.split("$")
            if len(parts) == 3:
                _, salt, key_hex = parts
                new_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100000)
                return hmac.compare_digest(new_key.hex(), key_hex)
        if _HAS_BCRYPT:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        return False
    except Exception:
        return False

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access"
    })
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT refresh token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta if expires_delta else timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "refresh"
    })
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str, expected_type: Optional[str] = None) -> Dict[str, Any]:
    """Decode and validate a signed JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        if expected_type and payload.get("type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type: expected {expected_type}",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
