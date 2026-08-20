"""
Defines the "shape" of data that flows through the LangGraph agent as it
processes an email, step by step.

Think of this as a shared clipboard passed from step to step - each step
reads what it needs off the clipboard and writes its own results back onto
it before handing it to the next step.
"""

import operator
from typing import Annotated, List, Optional, TypedDict

from app.schemas.analysis import EmailAnalysis


class EmailAgentState(TypedDict, total=False):
    # --- input: filled in before the agent starts ---
    message_id: str
    subject: str
    sender: str
    body_text: str

    # --- filled in as the agent runs ---
    analysis: Optional[EmailAnalysis]
    action_decision: str  # "no_action_needed" | "needs_further_processing"
    reply_draft: Optional[str]
    reply_validated: bool
    human_approval_required: bool
    human_approved: Optional[bool]
    action_executed: bool

    # A running trace of what the agent did, step by step - useful for
    # debugging now, and for showing "agent activity" in the dashboard later.
    #
    # `Annotated[..., operator.add]` is a LangGraph instruction: whenever a
    # step returns a "log" value, APPEND it to the existing list instead of
    # replacing it. Without this, each step would erase the previous step's
    # log entries.
    log: Annotated[List[str], operator.add]