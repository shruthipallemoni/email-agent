"""
Tests for Block 6 - LangGraph agent.

We again use a fake LLM provider (same idea as test_email_analysis.py) so
these tests run instantly, need no API key, and let us precisely control
what the "AI" decides - which is exactly what we need to test both
branches of the agent's decision-making.
"""

import json

import pytest

from app.agent.graph import run_email_agent
from app.services.llm.base import LLMProvider


class FakeLLMProvider(LLMProvider):
    def __init__(self, canned_response: str):
        self.canned_response = canned_response

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        return self.canned_response


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


@pytest.mark.asyncio
async def test_agent_takes_shortcut_when_no_response_needed():
    """
    When the AI decides an email doesn't need a reply (e.g. a newsletter),
    the agent should go STRAIGHT to store_result - skipping reply
    generation, validation, and approval entirely.
    """
    llm = FakeLLMProvider(_analysis_json(requires_response=False))

    final_state = await run_email_agent(
        llm,
        message_id="msg-1",
        subject="Weekly Newsletter",
        sender="news@example.com",
        body_text="Here's what happened this week...",
    )

    assert final_state["action_decision"] == "no_action_needed"
    assert "Analyzed email" in final_state["log"][0]
    assert any("Decided action: no_action_needed" in entry for entry in final_state["log"])

    # None of the "further processing" steps should have run.
    log_text = " ".join(final_state["log"])
    assert "Generate reply" not in log_text
    assert "Validate reply" not in log_text
    assert "human approval" not in log_text.lower()


@pytest.mark.asyncio
async def test_agent_goes_through_full_pipeline_when_response_needed():
    """
    When a reply IS needed, the agent should walk through every step:
    retrieve context, generate reply, validate, determine approval, human
    approval, execute action, then store result.
    """
    llm = FakeLLMProvider(_analysis_json(requires_response=True))

    final_state = await run_email_agent(
        llm,
        message_id="msg-2",
        subject="Can we reschedule?",
        sender="boss@company.com",
        body_text="Can we move tomorrow's meeting to Friday?",
    )

    assert final_state["action_decision"] == "needs_further_processing"
    assert final_state["human_approval_required"] is True

    log_text = " ".join(final_state["log"])
    assert "Retrieve context" in log_text
    assert "Generate reply" in log_text
    assert "Validate reply" in log_text
    assert "human approval is required" in log_text
    assert "Execute action" in log_text
    assert "Stored result" in log_text


@pytest.mark.asyncio
async def test_agent_state_carries_original_email_fields_through():
    """The email's basic info should survive unchanged to the final state."""
    llm = FakeLLMProvider(_analysis_json(requires_response=False))

    final_state = await run_email_agent(
        llm,
        message_id="msg-3",
        subject="Test Subject",
        sender="someone@example.com",
        body_text="Test body",
    )

    assert final_state["message_id"] == "msg-3"
    assert final_state["subject"] == "Test Subject"
    assert final_state["sender"] == "someone@example.com"


@pytest.mark.asyncio
async def test_agent_log_grows_rather_than_overwrites():
    """
    Confirms the `operator.add` annotation on the state's log field works -
    each step's log entries should ADD to the list, not replace it.
    """
    llm = FakeLLMProvider(_analysis_json(requires_response=True))

    final_state = await run_email_agent(
        llm,
        message_id="msg-4",
        subject="Test",
        sender="a@b.com",
        body_text="text",
    )

    # analyze_email, determine_action, retrieve_context, generate_reply,
    # validate_reply, determine_approval, human_approval, execute_action,
    # store_result = 9 steps, each logging at least one entry.
    assert len(final_state["log"]) >= 9