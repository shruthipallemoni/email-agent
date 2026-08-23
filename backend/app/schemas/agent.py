"""
Defines the shape of data returned when the frontend asks the agent to
process an email.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel

from app.schemas.analysis import EmailAnalysis
from app.schemas.reply import ReplyDraft
from app.schemas.validation import ReplyValidation


class SentMessageInfo(BaseModel):
    gmail_message_id: str
    thread_id: str


class AgentRunResponse(BaseModel):
    status: Literal["completed", "awaiting_approval"]
    message_id: str
    subject: str
    sender: str
    analysis: Optional[EmailAnalysis] = None
    action_decision: Optional[str] = None
    reply_draft: Optional[ReplyDraft] = None
    reply_validation: Optional[ReplyValidation] = None
    human_approval_required: Optional[bool] = None
    sent: Optional[SentMessageInfo] = None
    log: List[str] = []