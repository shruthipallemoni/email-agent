"""
Defines the shape of a validation check on an AI-drafted reply.
"""

from typing import List, Literal

from pydantic import BaseModel, Field

from app.schemas.analysis import EmailAnalysis
from app.schemas.reply import ReplyDraft


class ReplyValidation(BaseModel):
    passed: bool = Field(
        description="Whether the reply is safe and appropriate to show a human for approval"
    )
    issues: List[str] = Field(
        default_factory=list, description="Specific problems found, if any"
    )
    severity: Literal["none", "low", "medium", "high"] = Field(
        description="The highest severity of any issue found"
    )
    reasoning: str = Field(description="Brief explanation of the validation outcome")


class ValidatedReplyResponse(BaseModel):
    """Used by the standalone test endpoint that runs analyze -> draft -> validate in one call."""

    email_id: str
    subject: str
    from_: str
    analysis: EmailAnalysis
    draft: ReplyDraft
    validation: ReplyValidation