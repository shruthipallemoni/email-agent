"""
Tests for Block 2 - Authentication.

We can't fully test the real Google login here (that requires a real Google
account and browser), but we CAN test:
1. Our own JWT tokens are created and verified correctly.
2. /api/auth/login redirects toward Google.
3. /api/auth/me correctly reports "not logged in" when there's no cookie.
"""

from fastapi.testclient import TestClient

from app.core.security import create_access_token, decode_access_token
from app.main import app

client = TestClient(app)


def test_create_and_decode_access_token():
    token = create_access_token(user_email="test@example.com")
    email = decode_access_token(token)
    assert email == "test@example.com"


def test_decode_invalid_token_returns_none():
    assert decode_access_token("not-a-real-token") is None


def test_login_redirects_to_google():
    response = client.get("/api/auth/login", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert "accounts.google.com" in response.headers["location"]


def test_me_returns_not_authenticated_without_cookie():
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is False
    assert data["user"] is None