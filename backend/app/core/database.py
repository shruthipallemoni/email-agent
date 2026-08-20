"""
Sets up the connection to PostgreSQL using SQLAlchemy.

Quick concepts:
- "engine": the actual connection to the database.
- "SessionLocal": a factory that creates a new "conversation" (session) with
  the database for each request - we ask it questions, tell it to save
  changes, then close it when the request is done.
- "Base": every database table we define (in app/models/) will inherit from
  this, so SQLAlchemy knows about all of them.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    A FastAPI "dependency" - it opens a database session for a single
    request, hands it to the route function, and makes sure it's always
    closed afterward (even if something goes wrong).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()