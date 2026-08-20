"""
The actual login-related URLs (endpoints) the frontend calls.

The flow, step by step:

1. Frontend sends the user to GET /api/auth/login
2. We redirect the browser to Google's login/consent screen
3. User logs in and approves access on Google's site
4. Google redirects the browser back to GET /api/auth/callback with a code
5. We exchange that code for Google tokens + the user's profile info
6. We save the user in PostgreSQL and create OUR OWN session token,
   stored in a secure httpOnly cookie
7. Frontend can then call GET /api/auth/me to check "who is logged in?"
8. GET /api/auth/logout clears the cookie

Changed in Block 4: every function that needs user data now takes a "db"
(database session) argument, provided automatically by FastAPI via
Depends(get_db).
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.status import HTTP_401_UNAUTHORIZED

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, decode_access_token
from app.models.user import User
from app.schemas.auth import CurrentUser, LoginStatus
from app.services.oauth_service import oauth
from app.services.user_store import get_user, save_user

router = APIRouter()
settings = get_settings()


@router.get("/login")
async def login(request: Request):
    """Starts the Google login process by redirecting the browser to Google."""
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def callback(request: Request, db: Session = Depends(get_db)):
    """Google redirects here after the user approves access."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as exc:  # covers state mismatch, denied access, etc.
        raise HTTPException(status_code=400, detail=f"Google login failed: {exc}")

    userinfo = token.get("userinfo")
    if not userinfo or not userinfo.get("email"):
        raise HTTPException(status_code=400, detail="Google did not return user info")

    user = save_user(
        db,
        email=userinfo["email"],
        name=userinfo.get("name", userinfo["email"]),
        picture=userinfo.get("picture"),
        google_access_token=token["access_token"],
        google_refresh_token=token.get("refresh_token"),
    )

    session_token = create_access_token(user_email=user.email)

    # Send the user back to the frontend app, now logged in.
    response = RedirectResponse(url=settings.FRONTEND_URL)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,  # JavaScript on the page can't read this - protects against XSS theft
        secure=settings.ENVIRONMENT == "production",  # only send over HTTPS in production
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return response


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    A reusable "dependency" other routes can use to require login.
    Reads our session cookie, checks it's valid, and looks up the user
    in the database.
    """
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Not logged in")

    email = decode_access_token(token)
    if not email:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Session expired or invalid")

    user = get_user(db, email)
    if not user:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


@router.get("/me", response_model=LoginStatus)
def me(request: Request, db: Session = Depends(get_db)):
    """Lets the frontend check: is anyone logged in right now, and who?"""
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        return LoginStatus(authenticated=False)

    email = decode_access_token(token)
    if not email:
        return LoginStatus(authenticated=False)

    user = get_user(db, email)
    if not user:
        return LoginStatus(authenticated=False)

    return LoginStatus(
        authenticated=True,
        user=CurrentUser(email=user.email, name=user.name, picture=user.picture),
    )


@router.post("/logout")
def logout():
    """Logs the user out by deleting the session cookie."""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    return response