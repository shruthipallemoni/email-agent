"""
Tests for Block 3 - Gmail integration.

We can't call the real Gmail API in an automated test (it needs a real
logged-in Google account), so instead we test the two things that are most
likely to have bugs:
1. Parsing Gmail's raw message format into our simple summary/detail shape.
2. That the email routes correctly refuse access when nobody is logged in.
"""

import base64
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.reply import ReplyDraft
from app.services.gmail_service import (
    _build_reply_raw_message,
    _decode_base64url,
    _extract_plain_text_body,
    parse_message_detail,
    parse_message_summary,
    send_reply,
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


# --- Block 10: sending replies ---

import email as email_stdlib  # noqa: E402 (kept near its only use, for readability)


def test_parse_message_detail_extracts_message_id_header():
    message_with_id = dict(FAKE_MESSAGE)
    message_with_id["payload"] = dict(FAKE_MESSAGE["payload"])
    message_with_id["payload"]["headers"] = FAKE_MESSAGE["payload"]["headers"] + [
        {"name": "Message-ID", "value": "<abc123@mail.gmail.com>"}
    ]
    detail = parse_message_detail(message_with_id)
    assert detail["message_id_header"] == "<abc123@mail.gmail.com>"


def test_parse_message_detail_message_id_header_defaults_to_none():
    detail = parse_message_detail(FAKE_MESSAGE)  # no Message-ID header present
    assert detail["message_id_header"] is None


def test_build_reply_raw_message_contains_correct_headers_and_body():
    raw = _build_reply_raw_message(
        sender="me@company.com",
        to="boss@company.com",
        subject="Re: Meeting reschedule",
        body="Sure, Friday works.",
        in_reply_to="<original123@mail.gmail.com>",
    )
    # Decode it the same way Gmail itself would, to confirm it's valid.
    decoded_bytes = base64.urlsafe_b64decode(raw)
    parsed = email_stdlib.message_from_bytes(decoded_bytes)

    assert parsed["To"] == "boss@company.com"
    assert parsed["From"] == "me@company.com"
    assert parsed["Subject"] == "Re: Meeting reschedule"
    assert parsed["In-Reply-To"] == "<original123@mail.gmail.com>"
    assert parsed["References"] == "<original123@mail.gmail.com>"
    assert "Friday" in parsed.get_payload()


def test_build_reply_raw_message_omits_threading_headers_when_no_original_id():
    raw = _build_reply_raw_message(
        sender="me@company.com", to="boss@company.com",
        subject="Re: Test", body="Body text", in_reply_to=None,
    )
    decoded_bytes = base64.urlsafe_b64decode(raw)
    parsed = email_stdlib.message_from_bytes(decoded_bytes)

    assert parsed["In-Reply-To"] is None
    assert parsed["References"] is None


class _FakeUser:
    email = "me@company.com"
    google_access_token = "fake-token"
    google_refresh_token = "fake-refresh"


import pytest


@pytest.mark.asyncio
async def test_send_reply_calls_gmail_send_endpoint_with_correct_payload():
    """
    We don't hit the real network here - _gmail_post (which makes the
    actual HTTP call) is replaced with a fake that just records what it
    was asked to send, so we can check OUR code built the right request.
    """
    original_email = {
        "from_": "boss@company.com",
        "thread_id": "thread456",
        "message_id_header": "<original123@mail.gmail.com>",
    }
    draft = ReplyDraft(subject="Re: Meeting reschedule", body="Sure, Friday works.", notes="")

    fake_post = AsyncMock(return_value={"id": "sent-msg-1", "threadId": "thread456"})
    with patch("app.services.gmail_service._gmail_post", fake_post):
        result = await send_reply(db=None, user=_FakeUser(), original_email=original_email, draft=draft)

    assert result == {"id": "sent-msg-1", "threadId": "thread456"}

    # Check what send_reply actually asked _gmail_post to send.
    call_args = fake_post.call_args
    assert call_args.args[1] == "/messages/send"
    sent_json_body = call_args.kwargs["json_body"]
    assert sent_json_body["threadId"] == "thread456"
    assert "raw" in sent_json_body