"""
Tests for Block 8 - Reply validation.

Same fake-LLM approach as previous blocks. We test both layers of
validation separately: the rule-based checks (no AI needed) and how the
AI's opinion combines with them.
"""

import json

import pytest
from fastapi import HTTPException

from app.schemas.analysis import EmailAnalysis
from app.schemas.reply import ReplyDraft
from app.services.llm.base import LLMProvider
from app.services.reply_validation_service import validate_reply


class FakeLLMProvider(LLMProvider):
    def __init__(self, canned_response: str):
        self.canned_response = canned_response
        self.last_system_prompt = None
        self.last_user_prompt = None

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return self.canned_response


SAMPLE_ANALYSIS = EmailAnalysis(
    category="meeting",
    intent="reschedule tomorrow's meeting to Friday",
    urgency="medium",
    risk_level="low",
    requires_response=True,
    summary="The sender wants to move a meeting to Friday.",
    reasoning="Routine scheduling request.",
)

GOOD_DRAFT = ReplyDraft(
    subject="Re: Meeting reschedule",
    body="Hi, Friday works for me - let's move it there.",
    notes="Assumed Friday availability was fine.",
)


def _validation_json(passed=True, severity="none", issues=None) -> str:
    return json.dumps(
        {
            "passed": passed,
            "issues": issues or [],
            "severity": severity,
            "reasoning": "Looks good." if passed else "Found problems.",
        }
    )


@pytest.mark.asyncio
async def test_validate_reply_passes_a_clean_draft():
    llm = FakeLLMProvider(canned_response=_validation_json(passed=True))
    result = await validate_reply(
        llm, subject="Meeting", sender="boss@company.com", body_text="Move to Friday?",
        analysis=SAMPLE_ANALYSIS, draft=GOOD_DRAFT,
    )
    assert result.passed is True
    assert result.severity == "none"
    assert result.issues == []


@pytest.mark.asyncio
async def test_validate_reply_fails_when_llm_flags_an_issue():
    llm = FakeLLMProvider(
        canned_response=_validation_json(
            passed=False, severity="high", issues=["Reply confirms a payment that was never discussed."]
        )
    )
    result = await validate_reply(
        llm, subject="Test", sender="a@b.com", body_text="text",
        analysis=SAMPLE_ANALYSIS, draft=GOOD_DRAFT,
    )
    assert result.passed is False
    assert result.severity == "high"
    assert "payment" in result.issues[0]


@pytest.mark.asyncio
async def test_rule_based_check_catches_empty_body_even_if_ai_says_passed():
    """
    The rule-based layer should catch obvious problems EVEN IF the AI
    (wrongly) says everything looks fine - this is the whole point of
    having two independent layers.
    """
    empty_draft = ReplyDraft(subject="Re: Test", body="   ", notes="none")
    llm = FakeLLMProvider(canned_response=_validation_json(passed=True, severity="none"))

    result = await validate_reply(
        llm, subject="Test", sender="a@b.com", body_text="text",
        analysis=SAMPLE_ANALYSIS, draft=empty_draft,
    )
    assert result.passed is False
    assert any("empty" in issue.lower() for issue in result.issues)
    assert result.severity in ("medium", "high")


@pytest.mark.asyncio
async def test_rule_based_check_catches_leftover_placeholder_text():
    placeholder_draft = ReplyDraft(
        subject="Re: Test", body="Hi [Your Name], thanks for reaching out.", notes="none"
    )
    llm = FakeLLMProvider(canned_response=_validation_json(passed=True, severity="none"))

    result = await validate_reply(
        llm, subject="Test", sender="a@b.com", body_text="text",
        analysis=SAMPLE_ANALYSIS, draft=placeholder_draft,
    )
    assert result.passed is False
    assert any("placeholder" in issue.lower() for issue in result.issues)


@pytest.mark.asyncio
async def test_validate_reply_strips_markdown_code_fences():
    wrapped = f"```json\n{_validation_json(passed=True)}\n```"
    llm = FakeLLMProvider(canned_response=wrapped)
    result = await validate_reply(
        llm, subject="Test", sender="a@b.com", body_text="text",
        analysis=SAMPLE_ANALYSIS, draft=GOOD_DRAFT,
    )
    assert result.passed is True


@pytest.mark.asyncio
async def test_validate_reply_raises_on_invalid_json():
    llm = FakeLLMProvider(canned_response="not json at all")
    with pytest.raises(HTTPException) as exc_info:
        await validate_reply(
            llm, subject="Test", sender="a@b.com", body_text="text",
            analysis=SAMPLE_ANALYSIS, draft=GOOD_DRAFT,
        )
    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_both_original_email_and_draft_are_included_in_prompt():
    llm = FakeLLMProvider(canned_response=_validation_json(passed=True))
    await validate_reply(
        llm, subject="Meeting", sender="boss@company.com", body_text="Move to Friday?",
        analysis=SAMPLE_ANALYSIS, draft=GOOD_DRAFT,
    )
    assert "--- ORIGINAL EMAIL START ---" in llm.last_user_prompt
    assert "--- DRAFT REPLY START ---" in llm.last_user_prompt
    assert GOOD_DRAFT.body in llm.last_user_prompt


@pytest.mark.asyncio
async def test_system_prompt_instructs_model_to_ignore_embedded_instructions():
    llm = FakeLLMProvider(canned_response=_validation_json(passed=True))
    await validate_reply(
        llm, subject="Test", sender="a@b.com", body_text="text",
        analysis=SAMPLE_ANALYSIS, draft=GOOD_DRAFT,
    )
    assert "untrusted" in llm.last_system_prompt.lower()