"""
Handles all direct communication with Gmail's API.

Quick concepts explained:
- "access token": a temporary key (usually lasts ~1 hour) that proves we're
  allowed to read this user's Gmail.
- "refresh token": a longer-lasting key we can use to get a brand new access
  token, without asking the user to log in again.
- Gmail returns email bodies encoded in "base64url" (a text-safe way of
  representing raw bytes) - we have to decode that to get readable text.
"""

import base64
from typing import Any, Optional

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import User
from app.services.user_store import update_access_token

settings = get_settings()

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


async def _refresh_access_token(refresh_token: str) -> str:
    """Asks Google for a brand new access token using the refresh token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
    if response.status_code != 200:
        raise HTTPException(
            status_code=401,
            detail="Could not refresh Google access - please log in again.",
        )
    return response.json()["access_token"]


async def _gmail_get(db: Session, path: str, user: User, params: Optional[dict] = None) -> dict:
    """
    Makes a GET request to the Gmail API using the user's access token.
    If the token has expired (Gmail replies with 401), we automatically
    refresh it once and retry - so the user doesn't notice or get logged out
    just because an hour passed.
    """
    url = f"{GMAIL_API_BASE}{path}"
    headers = {"Authorization": f"Bearer {user.google_access_token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

        if response.status_code == 401:
            if not user.google_refresh_token:
                raise HTTPException(
                    status_code=401,
                    detail="Google access expired and no refresh token is available. Please log in again.",
                )
            new_token = await _refresh_access_token(user.google_refresh_token)
            update_access_token(db, user.email, new_token)
            user.google_access_token = new_token  # use the fresh token for the retry below
            headers = {"Authorization": f"Bearer {new_token}"}
            response = await client.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Gmail API error ({response.status_code}): {response.text}",
        )

    return response.json()


def _get_header(headers: list[dict], name: str) -> str:
    """Gmail stores subject/from/date etc. as a list of {name, value} pairs."""
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def _decode_base64url(data: str) -> str:
    """Gmail encodes email bodies in base64url - this turns it back into text."""
    padded = data + "=" * (-len(data) % 4)  # base64 needs padding to a multiple of 4
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _extract_plain_text_body(payload: dict) -> str:
    """
    Emails can be structured many ways (plain text, HTML, multipart with
    attachments...). This walks the structure looking for a plain-text part.
    If none exists, it falls back to an empty string rather than crashing.
    """
    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain" and payload.get("body", {}).get("data"):
        return _decode_base64url(payload["body"]["data"])

    for part in payload.get("parts", []) or []:
        text = _extract_plain_text_body(part)
        if text:
            return text

    # No plain text part found anywhere - fall back to raw HTML if present,
    # so we return something rather than nothing.
    if mime_type == "text/html" and payload.get("body", {}).get("data"):
        return _decode_base64url(payload["body"]["data"])

    return ""


def parse_message_summary(message: dict) -> dict:
    """Turns Gmail's raw message JSON into the small summary we show in a list."""
    headers = message.get("payload", {}).get("headers", [])
    return {
        "id": message["id"],
        "thread_id": message["threadId"],
        "subject": _get_header(headers, "Subject") or "(no subject)",
        "from_": _get_header(headers, "From"),
        "date": _get_header(headers, "Date"),
        "snippet": message.get("snippet", ""),
    }


def parse_message_detail(message: dict) -> dict:
    """Turns Gmail's raw message JSON into the full detail view of one email."""
    payload = message.get("payload", {})
    headers = payload.get("headers", [])
    return {
        "id": message["id"],
        "thread_id": message["threadId"],
        "subject": _get_header(headers, "Subject") or "(no subject)",
        "from_": _get_header(headers, "From"),
        "to": _get_header(headers, "To"),
        "date": _get_header(headers, "Date"),
        "snippet": message.get("snippet", ""),
        "body_text": _extract_plain_text_body(payload),
    }


async def list_recent_emails(
    db: Session, user: User, max_results: int = 10, query: str = ""
) -> list[dict]:
    """
    Fetches the most recent emails. Gmail's list endpoint only returns IDs,
    so we then fetch each message's details (in 'metadata' format, which is
    fast and gives us headers/snippet without downloading the full body).
    """
    list_params: dict[str, Any] = {"maxResults": max_results}
    if query:
        list_params["q"] = query

    list_data = await _gmail_get(db, "/messages", user, params=list_params)
    message_ids = [m["id"] for m in list_data.get("messages", [])]

    summaries = []
    for message_id in message_ids:
        detail = await _gmail_get(
            db,
            f"/messages/{message_id}",
            user,
            params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]},
        )
        summaries.append(parse_message_summary(detail))

    return summaries


async def get_email_detail(db: Session, user: User, message_id: str) -> dict:
    """Fetches one email in full, including its body text."""
    message = await _gmail_get(db, f"/messages/{message_id}", user, params={"format": "full"})
    return parse_message_detail(message)


async def get_thread(db: Session, user: User, thread_id: str) -> list[dict]:
    """Fetches every message in a thread (an email + all its replies)."""
    thread_data = await _gmail_get(db, f"/threads/{thread_id}", user, params={"format": "full"})
    return [parse_message_detail(message) for message in thread_data.get("messages", [])]