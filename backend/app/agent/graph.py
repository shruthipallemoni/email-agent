"""
Builds the LangGraph agent: wires the node functions from nodes.py into a
graph with branching logic, following the workflow from the project's
overall architecture plan.

Workflow:

START -> analyze_email -> determine_action
    -> (no response needed)        -> store_result -> END
    -> (needs further processing)  -> retrieve_context -> generate_reply
       -> validate_reply -> determine_approval
       -> [PAUSES HERE, waiting for a human]
       -> human_approval -> execute_action -> store_result -> END

Block 9 update: the graph now genuinely PAUSES before human_approval and
waits - possibly for minutes or hours - until a human approves or rejects
the draft through the API. Two LangGraph features make this possible:

1. `interrupt_before=["human_approval"]` on compile() - tells LangGraph to
   stop right before running that node, instead of running it immediately.
2. A CHECKPOINTER - saves the paused state somewhere durable (PostgreSQL,
   see app/agent/checkpointer.py) so it survives even if the server
   restarts before the human responds.

Because of this, build_email_agent_graph() now requires a checkpointer to
be passed in explicitly, rather than creating a throwaway one internally
(which is what Block 6 did, before pausing was possible).
"""

from typing import Optional

from langgraph.graph import END, StateGraph

from app.agent import nodes
from app.agent.state import EmailAgentState
from app.schemas.analysis import EmailAnalysis
from app.schemas.reply import ReplyDraft
from app.schemas.validation import ReplyValidation
from app.services.llm.base import LLMProvider


def build_email_agent_graph(llm: LLMProvider, checkpointer):
    """Assembles the graph. Cheap to call repeatedly - no I/O happens here."""
    graph = StateGraph(EmailAgentState)

    graph.add_node("analyze_email", nodes.make_analyze_email_node(llm))
    graph.add_node("determine_action", nodes.determine_action_node)
    graph.add_node("retrieve_context", nodes.retrieve_context_node)
    graph.add_node("generate_reply", nodes.make_generate_reply_node(llm))
    graph.add_node("validate_reply", nodes.make_validate_reply_node(llm))
    graph.add_node("determine_approval", nodes.determine_approval_node)
    graph.add_node("human_approval", nodes.human_approval_node)
    graph.add_node("execute_action", nodes.execute_action_node)
    graph.add_node("store_result", nodes.store_result_node)

    graph.set_entry_point("analyze_email")
    graph.add_edge("analyze_email", "determine_action")

    graph.add_conditional_edges(
        "determine_action",
        lambda state: state["action_decision"],
        {
            "no_action_needed": "store_result",
            "needs_further_processing": "retrieve_context",
        },
    )

    graph.add_edge("retrieve_context", "generate_reply")
    graph.add_edge("generate_reply", "validate_reply")
    graph.add_edge("validate_reply", "determine_approval")
    graph.add_edge("determine_approval", "human_approval")
    graph.add_edge("human_approval", "execute_action")
    graph.add_edge("execute_action", "store_result")
    graph.add_edge("store_result", END)

    return graph.compile(checkpointer=checkpointer, interrupt_before=["human_approval"])


def _initial_state(message_id: str, subject: str, sender: str, body_text: str) -> EmailAgentState:
    return {
        "message_id": message_id,
        "subject": subject,
        "sender": sender,
        "body_text": body_text,
        "log": [],
    }


def _thread_config(message_id: str) -> dict:
    # "thread_id" is how the checkpointer tells one email's agent run apart
    # from every other email's - using the email's own id keeps them separate.
    return {"configurable": {"thread_id": message_id}}


def _coerce_state_models(values: dict) -> dict:
    """
    Depending on the checkpointer backend, the structured fields we saved
    as Pydantic models (analysis, reply_draft, reply_validation) can come
    back as plain dictionaries after being stored and reloaded - this
    happens with the persistent PostgreSQL checkpointer, which serializes
    state to JSON. This converts them back into proper model instances so
    the rest of the app can use them normally (e.g. draft.subject instead
    of draft["subject"]).
    """
    values = dict(values)
    if isinstance(values.get("analysis"), dict):
        values["analysis"] = EmailAnalysis(**values["analysis"])
    if isinstance(values.get("reply_draft"), dict):
        values["reply_draft"] = ReplyDraft(**values["reply_draft"])
    if isinstance(values.get("reply_validation"), dict):
        values["reply_validation"] = ReplyValidation(**values["reply_validation"])
    return values


async def run_email_agent(
    llm: LLMProvider,
    checkpointer,
    message_id: str,
    subject: str,
    sender: str,
    body_text: str,
) -> EmailAgentState:
    """
    Starts a fresh agent run for one email. If a reply is needed, this
    PAUSES the run right before human_approval and returns the state as of
    that pause point - call resume_email_agent() later to continue it. If
    no reply is needed at all, the run finishes completely in this one call.
    """
    compiled_graph = build_email_agent_graph(llm, checkpointer)
    initial_state = _initial_state(message_id, subject, sender, body_text)
    return await compiled_graph.ainvoke(initial_state, config=_thread_config(message_id))


async def resume_email_agent(
    llm: LLMProvider,
    checkpointer,
    message_id: str,
    approved: bool,
    edited_draft: Optional[ReplyDraft] = None,
) -> EmailAgentState:
    """
    Resumes a paused agent run after a human has approved or rejected the
    drafted reply. Must use the SAME message_id given to run_email_agent,
    so the checkpointer can find where that run paused.

    `edited_draft`, if given, lets the human's edits to the reply (subject
    or body) replace the AI's draft before the run continues - a real
    human-in-the-loop workflow should let people fix small things rather
    than only choosing yes/no.
    """
    compiled_graph = build_email_agent_graph(llm, checkpointer)
    config = _thread_config(message_id)

    update_values: dict = {"human_approved": approved}
    if edited_draft is not None:
        update_values["reply_draft"] = edited_draft

    # Writes the human's decision into the paused state, then continues
    # the graph from exactly where it left off.
    await compiled_graph.aupdate_state(config, update_values)
    return await compiled_graph.ainvoke(None, config=config)


async def get_agent_state(llm: LLMProvider, checkpointer, message_id: str) -> tuple[dict, tuple]:
    """
    Reads back the current state of a run (paused or finished) WITHOUT
    running anything - used to show a pending approval in the dashboard.

    Returns (state_values, next_nodes):
    - state_values: {} if this message_id has no agent run at all, else
      the state dict as of right now.
    - next_nodes: which node(s) would run next. Empty if the run finished
      (or never started); contains "human_approval" if it's paused there.
    """
    compiled_graph = build_email_agent_graph(llm, checkpointer)
    snapshot = await compiled_graph.aget_state(_thread_config(message_id))
    return _coerce_state_models(snapshot.values), snapshot.next