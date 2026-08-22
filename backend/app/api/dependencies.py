"""
Shared FastAPI dependencies used across multiple route files.
"""

from fastapi import Request


def get_agent_checkpointer(request: Request):
    """
    Returns the shared, persistent LangGraph checkpointer created once at
    app startup (see the `lifespan` function in app/main.py). This is what
    lets the agent PAUSE on an email awaiting human approval and RESUME it
    later, even across server restarts.
    """
    return request.app.state.agent_checkpointer