"""
Tests for Block 4 - PostgreSQL persistence (using the SQLite test database
from conftest.py, which behaves the same way for these purposes).
"""

from app.services.user_store import get_user, save_user, update_access_token


def test_save_user_creates_new_user(db_session):
    user = save_user(
        db_session,
        email="alice@example.com",
        name="Alice",
        picture=None,
        google_access_token="access-1",
        google_refresh_token="refresh-1",
    )
    assert user.id is not None
    assert user.email == "alice@example.com"
    assert user.google_refresh_token == "refresh-1"


def test_get_user_returns_saved_user(db_session):
    save_user(
        db_session,
        email="bob@example.com",
        name="Bob",
        picture="http://example.com/pic.png",
        google_access_token="access-1",
        google_refresh_token="refresh-1",
    )
    found = get_user(db_session, "bob@example.com")
    assert found is not None
    assert found.name == "Bob"


def test_get_user_returns_none_when_not_found(db_session):
    assert get_user(db_session, "nobody@example.com") is None


def test_save_user_keeps_old_refresh_token_if_not_resent(db_session):
    """
    Google only sends a refresh token the FIRST time a user logs in.
    If they log in again and Google doesn't resend one, we must not
    overwrite the one we already have.
    """
    save_user(
        db_session,
        email="carol@example.com",
        name="Carol",
        picture=None,
        google_access_token="access-1",
        google_refresh_token="refresh-1",
    )
    updated = save_user(
        db_session,
        email="carol@example.com",
        name="Carol",
        picture=None,
        google_access_token="access-2",
        google_refresh_token=None,  # Google didn't resend one this time
    )
    assert updated.google_access_token == "access-2"
    assert updated.google_refresh_token == "refresh-1"  # preserved


def test_update_access_token_changes_only_the_token(db_session):
    save_user(
        db_session,
        email="dave@example.com",
        name="Dave",
        picture=None,
        google_access_token="old-token",
        google_refresh_token="refresh-1",
    )
    update_access_token(db_session, "dave@example.com", "new-token")

    updated = get_user(db_session, "dave@example.com")
    assert updated.google_access_token == "new-token"
    assert updated.name == "Dave"  # unaffected