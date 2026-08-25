"""
This file is the single place where the app reads its settings
(things like database address, app name, environment).

We use "pydantic-settings" so that:
- Settings can come from a .env file (a plain text file with KEY=VALUE lines).
- If a required setting is missing, the app tells us clearly instead of failing
  in a confusing way later.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # General app info
    APP_NAME: str = "AI Email & Productivity Agent"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = True

    # Backend server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Database connection (filled in later blocks, safe defaults for now)
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/email_agent"

    # Frontend URL (used later for CORS - letting the React app talk to the backend)
    FRONTEND_URL: str = "http://localhost:5173"

    # --- Google OAuth settings (Block 2) ---
    # These come from Google Cloud Console when you register the app.
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/callback"

    # Secret key used to sign our own login session tokens (JWT) and the
    # temporary OAuth state cookie. In production this must be a long,
    # random, secret value - never reuse the example one.
    SECRET_KEY: str = "dev-only-change-this-secret-key"
    SESSION_COOKIE_NAME: str = "email_agent_session"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # --- LLM settings (Block 5) ---
    # Which AI provider to use for understanding emails. Supported:
    # "anthropic", "openai", "gemini".
    LLM_PROVIDER: str = "anthropic"
    LLM_MODEL: str = "claude-sonnet-4-5"

    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # --- Observability settings (Block 12) ---
    # Optional: if left blank, the app runs exactly the same, just without
    # tracing. Get free keys at https://cloud.langfuse.com (see README).
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_BASE_URL: str = "https://cloud.langfuse.com"

    # This tells pydantic-settings to also look inside a file named ".env"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """
    Returns the settings, but only builds them once and reuses them after that
    (this is what @lru_cache does - it "remembers" the result of the first call).
    """
    return Settings()