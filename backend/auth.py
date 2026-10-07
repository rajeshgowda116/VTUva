import hashlib
import secrets
import time
from typing import Optional
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

try:
    from backend.database import get_db
    from backend.models import User
except ImportError:
    from database import get_db
    from models import User


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Generates a secure PBKDF2-HMAC-SHA256 password hash with salt."""
    if not salt:
        salt = secrets.token_hex(16)
    
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return key.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verifies cleartext password against stored hash & salt."""
    calc_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(calc_hash, password_hash)


def generate_user_token(user_id: int, email: str) -> str:
    """Generates secure random bearer session token."""
    raw = f"vtuva_{user_id}_{email}_{time.time()}_{secrets.token_hex(8)}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def get_current_user(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Retrieves current user from Bearer Token or X-User-ID header."""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]

    if token:
        user = db.query(User).filter(User.token == token).first()
        if user:
            return user

    if x_user_id:
        try:
            u_id = int(x_user_id)
            user = db.query(User).filter(User.id == u_id).first()
            if user:
                return user
        except ValueError:
            pass

    # Default fallback demo user
    default_user = db.query(User).filter(User.id == 1).first()
    if not default_user:
        p_hash, salt = hash_password("vtuva123")
        default_user = User(
            id=1,
            email="student@vtuva.ac.in",
            password_hash=p_hash,
            salt=salt,
            name="Rajesh Gouda",
            usn="4DM24AI038",
            semester="5th Semester",
            branch="AIML",
            token="vtuva_demo_token_2026"
        )
        db.add(default_user)
        db.commit()
        db.refresh(default_user)
    return default_user
