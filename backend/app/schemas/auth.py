"""
Defines the exact "shape" of data our auth API sends back to the frontend.

Using Pydantic models like this means FastAPI automatically checks the data
is correct, and automatically generates API documentation (at /docs).
"""

from typing import Optional

from pydantic import BaseModel


class CurrentUser(BaseModel):
    email: str
    name: str
    picture: Optional[str] = None


class LoginStatus(BaseModel):
    authenticated: bool
    user: Optional[CurrentUser] = None