"""
The email-related web addresses (endpoints) the frontend calls.

Every route here requires the user to be logged in (it reuses
get_current_user from Block 2) - you can't read someone's Gmail without
being that logged-in user.

Changed in Block 4: each route also takes a "db" (database session), which
gets passed down to gmail_service - it needs this only to save a refreshed
Google access token if the old one expired.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.agent import AgentRunResponse
from app.schemas.analysis import EmailAnalysisResponse
from app.schemas.email import EmailDetail, EmailListResponse, ThreadResponse
from app.services import gmail_service
from app.services.email_analysis_service import analyze_email
from app.services.llm.factory import get_llm_provider
from app.agent.graph import run_email_agent

router = APIRouter()


@router.get("", response_model=EmailListResponse)
async def list_emails(
    max_results: int = Query(default=10, ge=1, le=50),
    q: str = Query(default="", description="Optional Gmail search query, e.g. 'is:unread'"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns a list of the user's most recent emails."""
    emails = await gmail_service.list_recent_emails(db, user, max_results=max_results, query=q)
    return EmailListResponse(emails=emails, count=len(emails))


@router.get("/thread/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns every message in an email thread (an email + its replies)."""
    messages = await gmail_service.get_thread(db, user, thread_id)
    return ThreadResponse(thread_id=thread_id, messages=messages)


@router.get("/{message_id}", response_model=EmailDetail)
async def get_email(
    message_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns one email's full details, including its body text."""
    return await gmail_service.get_email_detail(db, user, message_id)


@router.post("/{message_id}/analyze", response_model=EmailAnalysisResponse)
async def analyze_email_route(
    message_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fetches one email and asks the AI to classify it: what it wants, how
    urgent/risky it is, and whether it needs a reply.
    """
    email = await gmail_service.get_email_detail(db, user, message_id)
    llm = get_llm_provider()
    analysis = await analyze_email(
        llm,
        subject=email["subject"],
        sender=email["from_"],
        body_text=email["body_text"],
    )
    return EmailAnalysisResponse(
        email_id=email["id"],
        subject=email["subject"],
        from_=email["from_"],
        analysis=analysis,
    )


@router.post("/{message_id}/run-agent", response_model=AgentRunResponse)
async def run_agent_route(
    message_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Runs the full LangGraph agent workflow on one email: analyze it, decide
    what (if anything) needs to happen, and record each step taken.

    Right now most of the workflow after "analyze" is placeholder logic -
    see app/agent/nodes.py for exactly which steps are real vs. stubbed,
    and which future block implements each one for real.
    """
    email = await gmail_service.get_email_detail(db, user, message_id)
    llm = get_llm_provider()

    final_state = await run_email_agent(
        llm,
        message_id=email["id"],
        subject=email["subject"],
        sender=email["from_"],
        body_text=email["body_text"],
    )

    return AgentRunResponse(
        message_id=final_state["message_id"],
        subject=final_state["subject"],
        sender=final_state["sender"],
        analysis=final_state.get("analysis"),
        action_decision=final_state.get("action_decision"),
        human_approval_required=final_state.get("human_approval_required"),
        log=final_state.get("log", []),
    )