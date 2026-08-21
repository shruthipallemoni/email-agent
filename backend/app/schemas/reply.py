"""
Defines the shape of an AI-drafted reply, and the response returned when
testing reply generation directly (outside the full agent pipeline).
"""

from pydantic import BaseModel, Field

from app.schemas.analysis import EmailAnalysis


class ReplyDraft(BaseModel):
    subject: str = Field(description="Suggested subject line for the reply, usually 'Re: ...'")
    body: str = Field(description="The drafted reply email body (no signature)")
    notes: str = Field(
        description="Any assumptions made, missing information, or things the user "
        "should double check before sending"
    )


class ReplyDraftResponse(BaseModel):
    email_id: str
    subject: str
    from_: str
    analysis: EmailAnalysis
    draft: ReplyDraft