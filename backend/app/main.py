import os

_provider = os.environ.get("SKILLSPECTOR_PROVIDER", "").strip()
_known_working = (
    (_provider == "anthropic" and bool(os.environ.get("ANTHROPIC_API_KEY", "").strip()))
    or (_provider == "openai" and bool(os.environ.get("OPENAI_API_KEY", "").strip()))
    or (_provider == "ollama")
)
if not _known_working:
    os.environ["SKILLSPECTOR_PROVIDER"] = "anthropic"
    os.environ["ANTHROPIC_API_KEY"] = "sk-placeholder-unlocks-llm-analyzer-wiring"

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from skillspector import __version__ as skillspector_version
from skillspector.llm_utils import is_llm_available
from skillspector.providers.claude_cli import ClaudeCLIProvider

from app.api.routes import admin, scan
from app.claude_login import kill_pending
from app.core.config import get_settings
from app.db import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    kill_pending()


app = FastAPI(title="Skillspector Web API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(scan.router)
app.include_router(admin.router)


@app.get("/health")
def health() -> dict:
    llm_available, _ = is_llm_available()

    previous_key = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        claude_cli_available, _ = ClaudeCLIProvider().is_available()
    finally:
        if previous_key is not None:
            os.environ["ANTHROPIC_API_KEY"] = previous_key

    return {
        "status": "ok",
        "skillspector_version": skillspector_version,
        "llm_available": llm_available,
        "claude_cli_available": claude_cli_available,
    }
