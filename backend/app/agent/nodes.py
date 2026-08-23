"""
Individual steps ("nodes") the LangGraph agent can take while processing an
email. Each node is a small function: it reads the current state, does one
job, and returns just the piece of state it changed.

One placeholder remains:
- Block 13 will implement retrieve_context_node for real (RAG)

Every other step is now real, including sending the approved reply -
though the actual Gmail API call for that lives in app/api/emails.py, not
in execute_action_node itself. See that function's docstring for why.
"""

from app.agent.state import EmailAgentState
from app.schemas.analysis import EmailAnalysis
from app.schemas.reply import ReplyDraft
from app.schemas.validation import ReplyValidation
from app.services.email_analysis_service import analyze_email
from app.services.reply_generation_service import generate_reply
from app.services.reply_validation_service import validate_reply
from app.services.llm.base import LLMProvider


def make_analyze_email_node(llm: LLMProvider):
    """
    Returns a node function that has access to `llm` (the AI provider)
    without needing it passed in through the state. This pattern is called
    a "closure" - it's how we give a node extra tools it needs to do its job.
    """

    async def analyze_email_node(state: EmailAgentState) -> dict:
        analysis: EmailAnalysis = await analyze_email(
            llm,
            subject=state["subject"],
            sender=state["sender"],
            body_text=state["body_text"],
        )
        return {
            "analysis": analysis,
            "log": [
                f"Analyzed email: category={analysis.category}, "
                f"urgency={analysis.urgency}, risk={analysis.risk_level}"
            ],
        }

    return analyze_email_node


def determine_action_node(state: EmailAgentState) -> dict:
    """
    REAL LOGIC (not a placeholder): reads the AI's analysis and decides
    whether anything needs to happen at all. This decision is what the
    graph uses next to choose which path to take.
    """
    analysis = state["analysis"]
    decision = "needs_further_processing" if analysis.requires_response else "no_action_needed"

    return {
        "action_decision": decision,
        "log": [f"Decided action: {decision}"],
    }


def retrieve_context_node(state: EmailAgentState) -> dict:
    """PLACEHOLDER - real RAG document/knowledge retrieval comes in Block 13."""
    return {"log": ["Retrieve context: skipped (not implemented until Block 13)"]}


def make_generate_reply_node(llm: LLMProvider):
    """
    Drafts a reply using the email content plus the analysis from the
    analyze_email step earlier in the graph. Same closure pattern as
    make_analyze_email_node - it's how this node gets access to `llm`.
    """

    async def generate_reply_node(state: EmailAgentState) -> dict:
        analysis = state["analysis"]
        draft: ReplyDraft = await generate_reply(
            llm,
            subject=state["subject"],
            sender=state["sender"],
            body_text=state["body_text"],
            analysis=analysis,
        )
        return {
            "reply_draft": draft,
            "log": [f"Generate reply: drafted subject='{draft.subject}'"],
        }

    return generate_reply_node


def make_validate_reply_node(llm: LLMProvider):
    """
    Reviews the draft from generate_reply against the original email,
    checking for fabricated commitments, risky content, or leftover
    placeholder text. Same closure pattern as the other AI-backed nodes.
    """

    async def validate_reply_node(state: EmailAgentState) -> dict:
        validation: ReplyValidation = await validate_reply(
            llm,
            subject=state["subject"],
            sender=state["sender"],
            body_text=state["body_text"],
            analysis=state["analysis"],
            draft=state["reply_draft"],
        )
        log_entry = f"Validate reply: passed={validation.passed}, severity={validation.severity}"
        if validation.issues:
            log_entry += f", issues={validation.issues}"

        return {
            "reply_validated": validation.passed,
            "reply_validation": validation,
            "log": [log_entry],
        }

    return validate_reply_node


def determine_approval_node(state: EmailAgentState) -> dict:
    """
    REAL LOGIC: for now, anything that reaches this point is marked as
    requiring human approval. This matches the project's security
    principle - sensitive actions require human approval by default,
    until real automation rules exist (Block 21).
    """
    return {
        "human_approval_required": True,
        "log": ["Determined human approval is required (default-safe until automation rules exist)"],
    }


def human_approval_node(state: EmailAgentState) -> dict:
    """
    REAL LOGIC: by the time this node actually runs, the graph has already
    PAUSED (LangGraph's "interrupt_before" feature - see graph.py) and a
    human has approved or rejected the draft through the API. This node
    doesn't do the approving itself - it just records the decision that
    was made, which was written into the state before the graph resumed.
    """
    approved = state.get("human_approved")
    log = f"Human approval: {'approved' if approved else 'rejected'} by user"
    return {"log": [log]}


def execute_action_node(state: EmailAgentState) -> dict:
    """
    Confirms whether the reply is cleared to send, based on the human's
    decision. The actual Gmail API call happens right after the graph
    finishes (see approve_reply_route() in app/api/emails.py) - not inside
    this node - which keeps the agent's "thinking" layer decoupled from
    Gmail-specific mechanics (the same separation used for reading email
    back in Block 3).
    """
    if state.get("human_approved"):
        return {
            "log": ["Execute action: approved - cleared to send via Gmail"],
        }
    return {
        "action_executed": False,
        "log": ["Execute action: skipped - human rejected the reply"],
    }


def store_result_node(state: EmailAgentState) -> dict:
    """
    REAL LOGIC (partially): records a final trace entry. Actually saving
    this permanently to PostgreSQL for the dashboard is planned for
    Block 12 - for now the log only exists for the length of this run.
    """
    return {"log": ["Stored result (in-memory only for now - persistent storage arrives in Block 12)"]}