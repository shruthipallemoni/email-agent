"""
Tests for Block 12 - observability.

The most important behavior to test here isn't Langfuse itself (we can't
call the real Langfuse service in a test), it's that our app works exactly
the same with ZERO configuration - nobody should be forced to sign up for
anything just to run this project.
"""

from app.services.observability import is_enabled, trace_llm_call


def test_observability_is_disabled_without_configured_keys():
    """In this test environment, no LANGFUSE_* keys are set - confirm we detect that."""
    assert is_enabled() is False


def test_trace_llm_call_yields_none_when_disabled():
    with trace_llm_call("test_call", "fake-model", "system", "user") as generation:
        assert generation is None
    # No exception, no network call attempted - this is the whole point.


def test_trace_llm_call_can_be_used_without_reading_the_yielded_value():
    """Callers are expected to check `if generation:` before using it - confirm that pattern works."""
    with trace_llm_call("test_call", "fake-model", "system", "user") as generation:
        if generation:
            generation.update(output="should never run in this test")
    # Reaching this line without error is the assertion.