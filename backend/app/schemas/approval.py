"""
Defines the shape of data for the human approval step: what a human sends
to approve/reject a draft, and what the dashboard sees while a draft is
waiting for a decision.
"""

from typing import Literal, Optional

from pydantic import BaseModel

from app.schemas.analysis import EmailAnalysis
from app.schemas.reply import ReplyDraft
from app.schemas.validation import ReplyValidation


class ApprovalDecisionRequest(BaseModel):
    approved: bool
    # Optional: lets a human tweak the AI's draft before approving it,
    # instead of only being able to accept or reject it as-is.
    edited_subject: Optional[str] = None
    edited_body: Optional[str] = None


class PendingApprovalResponse(BaseModel):
    status: Literal["awaiting_approval", "completed", "not_found"]
    message_id: str
    subject: Optional[str] = None
    sender: Optional[str] = None
    analysis: Optional[EmailAnalysis] = None
    reply_draft: Optional[ReplyDraft] = None
    reply_validation: Optional[ReplyValidation] = None