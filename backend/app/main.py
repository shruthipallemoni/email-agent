"""
This is the entry point of the backend server.

Running `uvicorn app.main:app` starts this file, which:
1. Creates the FastAPI application.
2. Turns on logging.
3. Allows the frontend (running on a different address) to talk to it (CORS).
4. Registers the routes (URLs) the app responds to - right now just /health.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.agent.checkpointer import close_checkpointer, init_checkpointer
from app.api.auth import router as auth_router
from app.api.emails import router as emails_router
from app.api.health import router as health_router
from app.services.observability import init_observability
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(debug=settings.DEBUG)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code before "yield" runs once when the server starts.
    logger.info("app_starting", environment=settings.ENVIRONMENT)

    # Sets up Langfuse tracing if configured (see app/services/observability.py) -
    # does nothing if no Langfuse keys are set in .env.
    init_observability()

    # Opens a persistent connection pool the agent uses to remember paused
    # runs (e.g. "waiting for human approval") across server restarts.
    app.state.agent_checkpointer = await init_checkpointer()

    yield

    # Code after "yield" runs once when the server shuts down.
    await close_checkpointer()


app = FastAPI(
    title=settings.APP_NAME,
    description="AI Personal Email & Productivity Agent - backend API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS = a security rule in browsers that blocks a website from calling a
# different website's API unless it's explicitly allowed. This line allows
# our React frontend to call this backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SessionMiddleware gives us a temporary, signed cookie that Authlib uses
# behind the scenes during the Google login redirect (to prevent a security
# issue called CSRF - a trick where another website could fake a login).
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(emails_router, prefix="/api/emails", tags=["emails"])


@app.get("/")
def root():
    return {"message": f"{settings.APP_NAME} backend is running"}