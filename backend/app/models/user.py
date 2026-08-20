"""
Defines the "users" table - this is where logged-in users and their Google
tokens are permanently stored, replacing the temporary in-memory version
from Block 2/3.
"""

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    picture = Column(String, nullable=True)

    # Google OAuth tokens (Block 2/3). In a later security-hardening block
    # these could be encrypted at rest - noted for now, not yet implemented.
    google_access_token = Column(String, nullable=False)
    google_refresh_token = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())