"""
Tests for Block 6 (LangGraph agent) and Block 9 (human-in-the-loop
approval).

We use a fake LLM provider (same idea as test_email_analysis.py) so these
tests run instantly, need no API key, and let us precisely control what
the "AI" decides. For the checkpointer, tests use LangGraph's in-memory
MemorySaver rather than the real PostgreSQL one (app/agent/checkpointer.py)
- no database needed to run these tests, and MemorySaver supports the same
pause/resume behavior we're testing.
"""

import json

import pytest
from langgraph.checkpoint.memory import MemorySaver

from app.agent.graph import get_agent_state, resume_email_agent, run_email_agent
from app.schemas.reply import ReplyDraft
from app.services.llm.base import LLMProvider


class FakeLLMProvider(LLMProvider):
    """
    A stand-in AI. Accepts either one response (reused for every call) or a
    list of responses returned in order - the agent makes multiple LLM
    calls per run (analyze, generate reply, validate), so tests that
    exercise the full pipeline need to supply one response per call.
    """

    def __init__(self, responses):
        self._responses = [responses] if isinstance(responses, str) else list(responses)
        self._call_count = 0

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        index = min(self._call_count, len(self._responses) - 1)
        self._call_count += 1
        return self._responses[index]


def _analysis_json(requires_response: bool, risk_level: str = "low") -> str:
    return json.dumps(
        {
            "category": "meeting",
            "intent": "test intent",
            "urgency": "medium",
            "risk_level": risk_level,
            "requires_response": requires_response,
            "summary": "A test email.",
            "reasoning": "Test reasoning.",
        }
    )


def _reply_json() -> str:
    return json.dumps(
        {
            "subject": "Re: Can we reschedule?",
            "body": "Sure, Friday works for me.",
            "notes": "Assumed Friday availability based on context.",
        }
    )


def _validation_json(passed: bool = True, severity: str = "none") -> str:
    return json.dumps(
        {
            "passed": passed,
            "issues": [],
            "severity": severity,
            "reasoning": "Looks good.",
        }
    )


@pytest.mark.asyncio
async def test_agent_takes_shortcut_when_no_response_needed():
    """
    When the AI decides an email doesn't need a reply (e.g. a newsletter),
    the agent should go STRAIGHT to store_result - skipping reply
    generation, validation, and approval entirely, with no pause at all.
    """
    llm = FakeLLMProvider(_analysis_json(requires_response=False))
    checkpointer = MemorySaver()

    final_state = await run_email_agent(
        llm, checkpointer,
        message_id="msg-1", subject="Weekly Newsletter",
        sender="news@example.com", body_text="Here's what happened this week...",
    )

    assert final_state["action_decision"] == "no_action_needed"
    log_text = " ".join(final_state["log"])
    assert "Generate reply" not in log_text
    assert "Validate reply" not in log_text
    assert "human approval" not in log_text.lower()
    assert "Stored result" in log_text  # finished completely, no pause


@pytest.mark.asyncio
async def test_agent_pauses_before_human_approval_when_response_needed():
    """
    When a reply IS needed, the first run_email_agent() call should stop
    right before human_approval - analysis, reply drafting, and validation
    should all have already happened, but nothing past that point yet.
    """
    llm = FakeLLMProvider([
        _analysis_json(requires_response=True), _reply_json(), _validation_json(passed=True),
    ])
    checkpointer = MemorySaver()

    final_state = await run_email_agent(
        llm, checkpointer,
        message_id="msg-2", subject="Can we reschedule?",
        sender="boss@company.com", body_text="Can we move tomorrow's meeting to Friday?",
    )

    assert final_state["action_decision"] == "needs_further_processing"
    assert final_state["reply_draft"].subject == "Re: Can we reschedule?"
    assert final_state["reply_validation"].passed is True
    assert final_state["human_approval_required"] is True

    log_text = " ".join(final_state["log"])
    assert "Generate reply" in log_text
    assert "Validate reply" in log_text
    # These steps come AFTER the pause point - they must NOT have run yet.
    assert "Human approval" not in log_text
    assert "Execute action" not in log_text
    assert "Stored result" not in log_text


@pytest.mark.asyncio
async def test_resume_after_approval_completes_the_run():
    llm = FakeLLMProvider([
        _analysis_json(requires_response=True), _reply_json(), _validation_json(passed=True),
    ])
    checkpointer = MemorySaver()

    await run_email_agent(
        llm, checkpointer,
        message_id="msg-3", subject="Can we reschedule?",
        sender="boss@company.com", body_text="Can we move tomorrow's meeting to Friday?",
    )

    final_state = await resume_email_agent(llm, checkpointer, "msg-3", approved=True)

    assert final_state["human_approved"] is True
    log_text = " ".join(final_state["log"])
    assert "Human approval: approved" in log_text
    assert "Execute action: approved" in log_text
    assert "Stored result" in log_text


@pytest.mark.asyncio
async def test_resume_after_rejection_skips_execution():
    llm = FakeLLMProvider([
        _analysis_json(requires_response=True), _reply_json(), _validation_json(passed=True),
    ])
    checkpointer = MemorySaver()

    await run_email_agent(
        llm, checkpointer,
        message_id="msg-4", subject="Can we reschedule?",
        sender="boss@company.com", body_text="text",
    )

    final_state = await resume_email_agent(llm, checkpointer, "msg-4", approved=False)

    log_text = " ".join(final_state["log"])
    assert "Human approval: rejected" in log_text
    assert "Execute action: skipped - human rejected" in log_text


@pytest.mark.asyncio
async def test_resume_with_edited_draft_uses_the_edited_text():
    """A human should be able to fix small things in the draft, not just approve/reject blindly."""
    llm = FakeLLMProvider([
        _analysis_json(requires_response=True), _reply_json(), _validation_json(passed=True),
    ])
    checkpointer = MemorySaver()

    await run_email_agent(
        llm, checkpointer,
        message_id="msg-5", subject="Can we reschedule?",
        sender="boss@company.com", body_text="text",
    )

    edited = ReplyDraft(
        subject="Re: Can we reschedule? (edited)",
        body="Actually, let's do Monday instead.",
        notes="original notes",
    )
    final_state = await resume_email_agent(
        llm, checkpointer, "msg-5", approved=True, edited_draft=edited
    )

    assert final_state["reply_draft"].subject == "Re: Can we reschedule? (edited)"
    assert "Monday" in final_state["reply_draft"].body


@pytest.mark.asyncio
async def test_get_agent_state_reports_awaiting_approval_while_paused():
    llm = FakeLLMProvider([
        _analysis_json(requires_response=True), _reply_json(), _validation_json(passed=True),
    ])
    checkpointer = MemorySaver()

    await run_email_agent(
        llm, checkpointer,
        message_id="msg-6", subject="Can we reschedule?",
        sender="boss@company.com", body_text="text",
    )

    values, next_nodes = await get_agent_state(llm, checkpointer, "msg-6")

    assert "human_approval" in next_nodes
    assert values["reply_draft"].subject == "Re: Can we reschedule?"


@pytest.mark.asyncio
async def test_get_agent_state_reports_completed_after_resume():
    llm = FakeLLMProvider([
        _analysis_json(requires_response=True), _reply_json(), _validation_json(passed=True),
    ])
    checkpointer = MemorySaver()

    await run_email_agent(
        llm, checkpointer,
        message_id="msg-7", subject="Test",
        sender="a@b.com", body_text="text",
    )
    await resume_email_agent(llm, checkpointer, "msg-7", approved=True)

    values, next_nodes = await get_agent_state(llm, checkpointer, "msg-7")

    assert next_nodes == ()
    assert values["action_executed"] is False  # placeholder until Block 10 sends for real


@pytest.mark.asyncio
async def test_get_agent_state_returns_empty_for_unknown_message():
    llm = FakeLLMProvider(_analysis_json(requires_response=False))
    checkpointer = MemorySaver()

    values, next_nodes = await get_agent_state(llm, checkpointer, "never-run-id")

    assert values == {}
    assert next_nodes == ()


@pytest.mark.asyncio
async def test_agent_state_carries_original_email_fields_through():
    """The email's basic info should survive unchanged to the final state."""
    llm = FakeLLMProvider(_analysis_json(requires_response=False))
    checkpointer = MemorySaver()

    final_state = await run_email_agent(
        llm, checkpointer,
        message_id="msg-8", subject="Test Subject",
        sender="someone@example.com", body_text="Test body",
    )

    assert final_state["message_id"] == "msg-8"
    assert final_state["subject"] == "Test Subject"
    assert final_state["sender"] == "someone@example.com"


@pytest.mark.asyncio
async def test_agent_log_grows_across_the_full_run_including_resume():
    """
    Confirms the `operator.add` annotation on the state's log field keeps
    working across a pause/resume boundary - the final log should contain
    entries from BOTH the initial run and the resumed portion.
    """
    llm = FakeLLMProvider([
        _analysis_json(requires_response=True), _reply_json(), _validation_json(passed=True),
    ])
    checkpointer = MemorySaver()

    await run_email_agent(
        llm, checkpointer,
        message_id="msg-9", subject="Test",
        sender="a@b.com", body_text="text",
    )
    final_state = await resume_email_agent(llm, checkpointer, "msg-9", approved=True)

    # analyze_email, determine_action, retrieve_context, generate_reply,
    # validate_reply, determine_approval, human_approval, execute_action,
    # store_result = 9 steps, each logging at least one entry.
    assert len(final_state["log"]) >= 9