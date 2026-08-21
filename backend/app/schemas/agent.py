"""
Defines the shape of data returned when the frontend asks the agent to
process an email.
"""

from typing import List, Optional

from pydantic import BaseModel

from app.schemas.analysis import EmailAnalysis
from app.schemas.reply import ReplyDraft


class AgentRunResponse(BaseModel):
    message_id: str
    subject: str
    sender: str
    analysis: Optional[EmailAnalysis] = None
    action_decision: Optional[str] = None
    reply_draft: Optional[ReplyDraft] = None
    human_approval_required: Optional[bool] = None
    log: List[str] = []