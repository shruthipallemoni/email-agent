"""
Builds the LangGraph agent: wires the node functions from nodes.py into a
graph with branching logic, following the workflow from the project's
overall architecture plan.

Workflow:

START -> analyze_email -> determine_action
    -> (no response needed)        -> store_result -> END
    -> (needs further processing)  -> retrieve_context -> generate_reply
       -> validate_reply -> determine_approval -> human_approval
       -> execute_action -> store_result -> END

Why LangGraph instead of just calling functions in order?
Because real agent workflows branch, like the "no response needed" shortcut
above. Later blocks will add more branching (e.g. "if validation fails, try
generating the reply again") and the ability to PAUSE mid-workflow to wait
for a human's approval, then resume later (Block 9). Plain sequential
function calls can't easily pause and resume - LangGraph is built for
exactly this, using something called a "checkpointer" (see below).
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agent import nodes
from app.agent.state import EmailAgentState
from app.services.llm.base import LLMProvider


def build_email_agent_graph(llm: LLMProvider):
    """Assembles the graph. Called fresh for each run (cheap - no I/O here)."""
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

    # This is the branching point: which path to take next depends on the
    # "action_decision" value that determine_action_node just wrote.
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

    # A "checkpointer" lets the graph's progress be saved and resumed later
    # instead of always running start-to-finish in one go. This will matter
    # a lot in Block 9, when the graph needs to PAUSE and wait for a human
    # to click "approve" before continuing - possibly minutes or hours
    # later. For now we use an in-memory checkpointer (MemorySaver); a
    # persistent, database-backed one can be swapped in later without
    # changing any node code.
    checkpointer = MemorySaver()

    return graph.compile(checkpointer=checkpointer)


async def run_email_agent(
    llm: LLMProvider,
    message_id: str,
    subject: str,
    sender: str,
    body_text: str,
) -> EmailAgentState:
    """Runs the whole agent workflow for one email and returns the final state."""
    compiled_graph = build_email_agent_graph(llm)

    initial_state: EmailAgentState = {
        "message_id": message_id,
        "subject": subject,
        "sender": sender,
        "body_text": body_text,
        "log": [],
    }

    # "thread_id" is how LangGraph's checkpointer tracks one specific run -
    # using the email's own id keeps each email's agent run separate from
    # every other email's.
    config = {"configurable": {"thread_id": message_id}}

    final_state = await compiled_graph.ainvoke(initial_state, config=config)
    return final_state