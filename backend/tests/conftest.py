"""
Shared test setup (pytest automatically finds and uses this file).

Instead of connecting to a real PostgreSQL server just to run tests, we use
SQLite's in-memory mode - it behaves enough like a real database for our
tests, and needs no setup at all. Every test gets a clean, empty database.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.user import User

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # keeps the same in-memory database across connections
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Only tables listed here get created in the SQLite test database. This is
# deliberately a whitelist, not "all of Base.metadata" - Block 13 added a
# `Vector` column (from pgvector) to document_chunks, and that column type
# only exists in real PostgreSQL, not SQLite. Tests involving RAG/knowledge
# base features use mocks instead (see test_knowledge_service.py) rather
# than a real database - only a live Postgres+pgvector instance can
# actually exercise that table.
_SQLITE_COMPATIBLE_TABLES = [User.__table__]


def _override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_test_database():
    """Runs before/after every test: creates fresh tables, then drops them."""
    Base.metadata.create_all(bind=test_engine, tables=_SQLITE_COMPATIBLE_TABLES)
    app.dependency_overrides[get_db] = _override_get_db
    yield
    Base.metadata.drop_all(bind=test_engine, tables=_SQLITE_COMPATIBLE_TABLES)
    app.dependency_overrides.clear()


@pytest.fixture
def db_session():
    """Gives a test direct access to a database session, when needed."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()