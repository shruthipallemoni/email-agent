"""
Sets up the connection to Google's OAuth system using a library called
"Authlib" (this saves us from manually handling a lot of tricky, easy-to-
get-wrong security details of the OAuth process).

What "scopes" means below: when we send the user to Google to log in, we
also ask permission for certain things. Right now we ask for:
- their email and basic profile (to know who they are)
- readonly Gmail access (so later blocks can read emails)
We are NOT asking for send/delete access yet - we'll only request more
sensitive permissions in a later block, once we actually build that feature.
This follows the security principle of asking only for what we need.
"""

from authlib.integrations.starlette_client import OAuth

from app.core.config import get_settings

settings = get_settings()

oauth = OAuth()

oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    access_token_url="https://oauth2.googleapis.com/token",
    jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
    userinfo_endpoint="https://openidconnect.googleapis.com/v1/userinfo",
    client_kwargs={
        "scope": (
            "openid email profile "
            "https://www.googleapis.com/auth/gmail.readonly"
        ),
        # Asking for a refresh token so we can access Gmail later without
        # the user having to log in again every hour.
        "access_type": "offline",
        "prompt": "consent",
    },
)