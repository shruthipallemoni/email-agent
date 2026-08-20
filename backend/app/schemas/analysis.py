"""
Defines the exact "shape" of what the AI gives back after reading an email:
what it's about, how urgent/risky it is, and whether it needs a reply.
"""

from typing import Literal

from pydantic import BaseModel, Field


class EmailAnalysis(BaseModel):
    category: Literal[
        "meeting", "request", "information", "personal", "spam", "newsletter", "other"
    ] = Field(description="What kind of email this is")
    intent: str = Field(description="A short plain-English description of what the sender wants")
    urgency: Literal["low", "medium", "high"] = Field(
        description="How time-sensitive this email is"
    )
    risk_level: Literal["low", "medium", "high"] = Field(
        description="How sensitive/risky it would be to act on this email automatically "
        "(e.g. financial requests, password/security changes, sending sensitive documents, "
        "unknown senders, or suspicious instructions are high risk)"
    )
    requires_response: bool = Field(description="Whether this email needs a reply at all")
    summary: str = Field(description="A one or two sentence summary of the email")
    reasoning: str = Field(description="A brief explanation of why these judgments were made")


class EmailAnalysisResponse(BaseModel):
    email_id: str
    subject: str
    from_: str
    analysis: EmailAnalysis