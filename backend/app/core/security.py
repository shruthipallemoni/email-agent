"""
Handles creating and checking our own login tokens (JWT).

Quick explanation of a JWT ("JSON Web Token"):
It's a small piece of text that proves "this user is logged in" without the
server needing to remember every logged-in user in memory. It's signed with
our SECRET_KEY, so if anyone tries to tamper with it, the signature check
fails and we reject it.

Note: this is SEPARATE from the Google OAuth token. Google's token lets us
call Gmail on the user's behalf. Our own JWT just lets the FRONTEND know
"this browser is logged in as this user" via a secure cookie.
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

ALGORITHM = "HS256"


def create_access_token(user_email: str) -> str:
    """Builds a signed token containing the user's email and an expiry time."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_email, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """
    Checks a token is valid and not expired.
    Returns the user's email if valid, or None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None