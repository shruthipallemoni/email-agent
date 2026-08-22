"""
Provides a checkpointer for the LangGraph agent.

This implementation uses an in-memory checkpointer for development/testing.
For production use with persistent state across server restarts, consider
integrating a database-backed checkpointer from langgraph-checkpoint.
"""

from langgraph.checkpoint.memory import MemorySaver

_checkpointer = None


async def init_checkpointer():
    """
    Initializes the checkpointer for the agent.
    Called once when the app starts up (see the `lifespan` function in app/main.py).
    """
    global _checkpointer
    _checkpointer = MemorySaver()
    return _checkpointer


async def close_checkpointer():
    """Closes the checkpointer cleanly when the app shuts down."""
    global _checkpointer
    _checkpointer = None