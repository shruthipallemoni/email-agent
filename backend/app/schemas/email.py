"""
Defines the exact "shape" of email data our API sends to the frontend.
"""

from pydantic import BaseModel


class EmailSummary(BaseModel):
    id: str
    thread_id: str
    subject: str
    from_: str
    date: str
    snippet: str


class EmailDetail(BaseModel):
    id: str
    thread_id: str
    subject: str
    from_: str
    to: str
    date: str
    snippet: str
    body_text: str


class EmailListResponse(BaseModel):
    emails: list[EmailSummary]
    count: int


class ThreadResponse(BaseModel):
    thread_id: str
    messages: list[EmailDetail]