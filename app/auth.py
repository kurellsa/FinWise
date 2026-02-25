"""
Multi-user auth using a signed session cookie.
Cookie payload: {"id": user_id, "un": username}
No DB lookup needed per request to get username for navbar.
"""
import os
from typing import Optional
import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, HTTPException
from dotenv import load_dotenv

load_dotenv()

_SECRET_KEY = os.environ["SECRET_KEY"]
_serializer = URLSafeTimedSerializer(_SECRET_KEY)
COOKIE_NAME = "fw_session"
SESSION_MAX_AGE = 60 * 60 * 8   # 8 hours


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_session_cookie(response, user_id: int, username: str) -> None:
    token = _serializer.dumps({"id": user_id, "un": username})
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=SESSION_MAX_AGE,
        samesite="lax",
    )


def get_current_user(request: Request) -> Optional[tuple[int, str]]:
    """Returns (user_id, username) from the session cookie, or None."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        payload = _serializer.loads(token, max_age=SESSION_MAX_AGE)
        return (payload["id"], payload["un"])
    except (BadSignature, SignatureExpired, KeyError):
        return None


def require_auth(request: Request) -> tuple[int, str]:
    """Returns (user_id, username) or raises 302 to /login."""
    session = get_current_user(request)
    if not session:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return session
