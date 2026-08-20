"""
Tests for Block 3 - Gmail integration.

We can't call the real Gmail API in an automated test (it needs a real
logged-in Google account), so instead we test the two things that are most
likely to have bugs:
1. Parsing Gmail's raw message format into our simple summary/detail shape.
2. That the email routes correctly refuse access when nobody is logged in.
"""

import base64

from fastapi.testclient import TestClient

from app.main import app
from app.services.gmail_service import (
    _decode_base64url,
    _extract_plain_text_body,
    parse_message_detail,
    parse_message_summary,
)

client = TestClient(app)


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8")


FAKE_MESSAGE = {
    "id": "msg123",
    "threadId": "thread456",
    "snippet": "Hey, can we move tomorrow's meeting to Friday?",
    "payload": {
        "mimeType": "multipart/alternative",
        "headers": [
            {"name": "Subject", "value": "Meeting reschedule"},
            {"name": "From", "value": "boss@company.com"},
            {"name": "To", "value": "me@company.com"},
            {"name": "Date", "value": "Tue, 18 Aug 2026 10:00:00 +0000"},
        ],
        "parts": [
            {
                "mimeType": "text/plain",
                "body": {"data": _b64("Hey, can we move tomorrow's meeting to Friday?")},
            },
            {
                "mimeType": "text/html",
                "body": {"data": _b64("<p>Hey, can we move tomorrow's meeting to Friday?</p>")},
            },
        ],
    },
}


def test_decode_base64url_roundtrip():
    encoded = _b64("hello world")
    assert _decode_base64url(encoded) == "hello world"


def test_extract_plain_text_prefers_text_plain_part():
    body = _extract_plain_text_body(FAKE_MESSAGE["payload"])
    assert body == "Hey, can we move tomorrow's meeting to Friday?"
    assert "<p>" not in body  # confirms it picked plain text, not the html part


def test_parse_message_summary():
    summary = parse_message_summary(FAKE_MESSAGE)
    assert summary["id"] == "msg123"
    assert summary["thread_id"] == "thread456"
    assert summary["subject"] == "Meeting reschedule"
    assert summary["from_"] == "boss@company.com"


def test_parse_message_detail_includes_body():
    detail = parse_message_detail(FAKE_MESSAGE)
    assert detail["to"] == "me@company.com"
    assert "Friday" in detail["body_text"]


def test_parse_message_summary_handles_missing_subject():
    message = {
        "id": "msg789",
        "threadId": "thread789",
        "snippet": "no subject here",
        "payload": {"headers": []},
    }
    summary = parse_message_summary(message)
    assert summary["subject"] == "(no subject)"


def test_list_emails_requires_login():
    response = client.get("/api/emails")
    assert response.status_code == 401


def test_get_email_requires_login():
    response = client.get("/api/emails/msg123")
    assert response.status_code == 401


def test_get_thread_requires_login():
    response = client.get("/api/emails/thread/thread456")
    assert response.status_code == 401