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

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from skillspector import __version__ as skillspector_version
from skillspector.llm_utils import is_llm_available

from app import db, retention
from app.api.routes import admin, scan
from app.api.routes import settings as settings_routes
from app.claude_login import is_claude_cli_available, kill_pending
from app.core.config import get_settings
from app.core.mode import check_mode
from app.db import init_db
from app.scan_logs import init_logging

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_mode(settings)
    init_db()
    # Jobs run in this process, so anything still pending/running from a previous one is dead.
    db.fail_unfinished_scans(error="Interrupted: the API restarted before this scan finished", finished_at=time.time())
    init_logging()
    retention.start()
    yield
    retention.stop()
    kill_pending()


app = FastAPI(title="Skillspector Web API", version="1.1.1", lifespan=lifespan)  # x-release-please-version

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(scan.router)
app.include_router(admin.router)
app.include_router(settings_routes.router)


@app.get("/health")
def health() -> dict:
    llm_available, _ = is_llm_available()
    return {
        "status": "ok",
        "mode": settings.mode.value,
        "skillspector_version": skillspector_version,
        "llm_available": llm_available,
        "claude_cli_available": is_claude_cli_available(),
    }
