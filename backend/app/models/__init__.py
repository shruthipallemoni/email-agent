"""
Importing every model here means that anywhere the app imports
`app.models`, all tables get registered with SQLAlchemy's Base - this
matters for both Alembic (migrations) and test database setup.
"""

from app.models.user import User  # noqa: F401
from app.models.document import Document, DocumentChunk  # noqa: F401