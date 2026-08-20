"""
Reads and writes users using the real database (PostgreSQL).

This replaces the temporary in-memory version from Block 2/3. Notice the
function names are the same as before (save_user, get_user,
update_access_token) - only a database session ("db") argument was added.
That's intentional: the rest of the app barely had to change.

IMPORTANT: unlike before, a restart of the server no longer logs everyone
out or forgets their Google tokens - it's now saved permanently.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User


def save_user(
    db: Session,
    email: str,
    name: str,
    picture: Optional[str],
    google_access_token: str,
    google_refresh_token: Optional[str],
) -> User:
    """Creates a new user, or updates an existing one if they log in again."""
    user = db.query(User).filter(User.email == email).first()

    if user:
        user.name = name
        user.picture = picture
        user.google_access_token = google_access_token
        # Google only sends a refresh token the FIRST time a user approves
        # access - if we don't get a new one, keep the existing one.
        if google_refresh_token:
            user.google_refresh_token = google_refresh_token
    else:
        user = User(
            email=email,
            name=name,
            picture=picture,
            google_access_token=google_access_token,
            google_refresh_token=google_refresh_token,
        )
        db.add(user)

    db.commit()
    db.refresh(user)  # reloads the user with any database-generated values (like id)
    return user


def get_user(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def update_access_token(db: Session, email: str, new_access_token: str) -> None:
    """Called after we refresh an expired Google access token."""
    user = get_user(db, email)
    if user:
        user.google_access_token = new_access_token
        db.commit()