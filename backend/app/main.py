import logging
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

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from skillspector import __version__ as skillspector_version
from skillspector.llm_utils import is_llm_available

from app import retention
from app.api.routes import account, admin, auth, backoffice, internal, scan, users
from app.api.routes import settings as settings_routes
from app.auth import auth_mode
from app.claude_login import is_claude_cli_available, kill_pending
from app.core.config import get_settings
from app.core.mode import Mode, check_mode
from app.db import init_db
from app.jobs import get_runner
from app.scan_logs import init_logging

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_mode(settings)
    if os.environ.get("SKILLSPECTOR_WEB_ADMIN_TOKEN"):
        logging.getLogger("uvicorn.error").warning(
            "SKILLSPECTOR_WEB_ADMIN_TOKEN is no longer used and can be removed. "
            "Admin access now follows SKILLSPECTOR_WEB_AUTH: with 'none' (the default) anyone who can "
            "reach the server has full access; with 'accounts', admins sign in."
        )
    init_db()
    get_runner().on_startup()
    init_logging()
    # Hosted, Vercel Cron runs the sweep (POST /internal/retention): no process lives long enough.
    if settings.mode is Mode.SELF_HOSTED:
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

@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """FastAPI's default 422 echoes the submitted values back, which for a scan request includes
    the API key. Keep where and why, drop what was sent."""
    errors = [{k: v for k, v in error.items() if k not in ("input", "ctx", "url")} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})


app.include_router(auth.router)
app.include_router(account.router)
app.include_router(users.router)
app.include_router(backoffice.router)
app.include_router(scan.router)
app.include_router(admin.router)
app.include_router(settings_routes.router)
app.include_router(internal.router)


@app.get("/health")
def health() -> dict:
    llm_available, _ = is_llm_available()
    return {
        "status": "ok",
        "mode": settings.mode.value,
        "auth": auth_mode(),
        "skillspector_version": skillspector_version,
        "llm_available": llm_available,
        # Hosted servers have no shared Claude login to check.
        "claude_cli_available": settings.mode is Mode.SELF_HOSTED and is_claude_cli_available(),
    }
