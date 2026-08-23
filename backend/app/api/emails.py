"""
The email-related web addresses (endpoints) the frontend calls.

Every route here requires the user to be logged in (it reuses
get_current_user from Block 2) - you can't read someone's Gmail without
being that logged-in user.

Changed in Block 4: each route also takes a "db" (database session), which
gets passed down to gmail_service - it needs this only to save a refreshed
Google access token if the old one expired.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.api.dependencies import get_agent_checkpointer
from app.core.database import get_db
from app.models.user import User
from app.schemas.agent import AgentRunResponse, SentMessageInfo
from app.schemas.analysis import EmailAnalysisResponse
from app.schemas.approval import ApprovalDecisionRequest, PendingApprovalResponse
from app.schemas.email import EmailDetail, EmailListResponse, ThreadResponse
from app.schemas.reply import ReplyDraft, ReplyDraftResponse
from app.schemas.validation import ValidatedReplyResponse
from app.services import gmail_service
from app.services.email_analysis_service import analyze_email
from app.services.reply_generation_service import generate_reply
from app.services.reply_validation_service import validate_reply
from app.services.llm.factory import get_llm_provider
from app.agent.graph import get_agent_state, resume_email_agent, run_email_agent

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
    checkpointer=Depends(get_agent_checkpointer),
):
    """
    Runs the LangGraph agent workflow on one email: analyze it, decide what
    (if anything) needs to happen, draft and validate a reply if needed,
    then PAUSE and wait for a human to approve or reject it.

    If the email doesn't need a reply at all (e.g. a newsletter), the run
    finishes completely in this one call - no approval needed.

    See app/agent/nodes.py for exactly which steps are real vs. still
    placeholders, and which future block implements each remaining one.
    """
    email = await gmail_service.get_email_detail(db, user, message_id)
    llm = get_llm_provider()

    final_state = await run_email_agent(
        llm,
        checkpointer,
        message_id=email["id"],
        subject=email["subject"],
        sender=email["from_"],
        body_text=email["body_text"],
    )

    status = "completed" if final_state.get("action_decision") == "no_action_needed" else "awaiting_approval"

    return AgentRunResponse(
        status=status,
        message_id=final_state["message_id"],
        subject=final_state["subject"],
        sender=final_state["sender"],
        analysis=final_state.get("analysis"),
        action_decision=final_state.get("action_decision"),
        reply_draft=final_state.get("reply_draft"),
        reply_validation=final_state.get("reply_validation"),
        human_approval_required=final_state.get("human_approval_required"),
        log=final_state.get("log", []),
    )


@router.post("/{message_id}/validate-reply", response_model=ValidatedReplyResponse)
async def validate_reply_route(
    message_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Runs analyze -> draft -> validate in one call - useful for testing
    reply validation directly without running the full agent pipeline.
    """
    email = await gmail_service.get_email_detail(db, user, message_id)
    llm = get_llm_provider()

    analysis = await analyze_email(
        llm, subject=email["subject"], sender=email["from_"], body_text=email["body_text"]
    )
    draft = await generate_reply(
        llm,
        subject=email["subject"],
        sender=email["from_"],
        body_text=email["body_text"],
        analysis=analysis,
    )
    validation = await validate_reply(
        llm,
        subject=email["subject"],
        sender=email["from_"],
        body_text=email["body_text"],
        analysis=analysis,
        draft=draft,
    )

    return ValidatedReplyResponse(
        email_id=email["id"],
        subject=email["subject"],
        from_=email["from_"],
        analysis=analysis,
        draft=draft,
        validation=validation,
    )


@router.post("/{message_id}/generate-reply", response_model=ReplyDraftResponse)
async def generate_reply_route(
    message_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Analyzes an email and drafts a reply, in one call - useful for testing
    reply generation directly without running the full agent pipeline.
    """
    email = await gmail_service.get_email_detail(db, user, message_id)
    llm = get_llm_provider()

    analysis = await analyze_email(
        llm, subject=email["subject"], sender=email["from_"], body_text=email["body_text"]
    )
    draft = await generate_reply(
        llm,
        subject=email["subject"],
        sender=email["from_"],
        body_text=email["body_text"],
        analysis=analysis,
    )

    return ReplyDraftResponse(
        email_id=email["id"],
        subject=email["subject"],
        from_=email["from_"],
        analysis=analysis,
        draft=draft,
    )


@router.get("/{message_id}/pending-approval", response_model=PendingApprovalResponse)
async def get_pending_approval_route(
    message_id: str,
    user: User = Depends(get_current_user),
    checkpointer=Depends(get_agent_checkpointer),
):
    """
    Checks whether an email's agent run is currently paused, waiting for a
    human decision - and if so, returns everything needed to show it in
    the dashboard (the draft reply, its validation, etc).
    """
    llm = get_llm_provider()
    values, next_nodes = await get_agent_state(llm, checkpointer, message_id)

    if not values:
        return PendingApprovalResponse(status="not_found", message_id=message_id)

    status = "awaiting_approval" if "human_approval" in next_nodes else "completed"

    return PendingApprovalResponse(
        status=status,
        message_id=message_id,
        subject=values.get("subject"),
        sender=values.get("sender"),
        analysis=values.get("analysis"),
        reply_draft=values.get("reply_draft"),
        reply_validation=values.get("reply_validation"),
    )


@router.post("/{message_id}/approve", response_model=AgentRunResponse)
async def approve_reply_route(
    message_id: str,
    decision: ApprovalDecisionRequest,
    user: User = Depends(get_current_user),
    checkpointer=Depends(get_agent_checkpointer),
    db: Session = Depends(get_db),
):
    """
    Submits a human's approve/reject decision for a paused agent run, and
    resumes it. Optionally, the human can edit the draft's subject/body
    before approving - their edits are used instead of the AI's original
    draft for the rest of the run.

    If approved, this is the ONLY place in the whole app that actually
    sends an email through Gmail - matching the project's security
    principle that sensitive actions require explicit human approval first.
    """
    llm = get_llm_provider()
    values, next_nodes = await get_agent_state(llm, checkpointer, message_id)

    if not values or "human_approval" not in next_nodes:
        raise HTTPException(
            status_code=404,
            detail="No pending approval found for this email. It may already have been "
            "approved/rejected, or the agent hasn't been run on it yet.",
        )

    edited_draft = None
    if decision.edited_subject is not None or decision.edited_body is not None:
        current_draft: ReplyDraft = values["reply_draft"]
        edited_draft = ReplyDraft(
            subject=decision.edited_subject or current_draft.subject,
            body=decision.edited_body or current_draft.body,
            notes=current_draft.notes,
        )

    final_state = await resume_email_agent(
        llm, checkpointer, message_id, approved=decision.approved, edited_draft=edited_draft
    )

    sent_info = None
    if decision.approved and final_state.get("action_decision") == "needs_further_processing":
        validation = final_state.get("reply_validation")
        if validation and not validation.passed:
            final_state["log"].append(
                f"Note: reply failed automated validation (severity={validation.severity}) "
                "but was approved by human override."
            )

        original_email = await gmail_service.get_email_detail(db, user, message_id)
        send_result = await gmail_service.send_reply(
            db, user, original_email, final_state["reply_draft"]
        )
        sent_info = SentMessageInfo(
            gmail_message_id=send_result["id"], thread_id=send_result["threadId"]
        )
        final_state["log"].append(f"Sent via Gmail (message id: {send_result['id']})")

    return AgentRunResponse(
        status="completed",
        message_id=final_state["message_id"],
        subject=final_state["subject"],
        sender=final_state["sender"],
        analysis=final_state.get("analysis"),
        action_decision=final_state.get("action_decision"),
        reply_draft=final_state.get("reply_draft"),
        reply_validation=final_state.get("reply_validation"),
        human_approval_required=final_state.get("human_approval_required"),
        sent=sent_info,
        log=final_state.get("log", []),
    )