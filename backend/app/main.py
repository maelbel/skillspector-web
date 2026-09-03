from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from skillspector import __version__ as skillspector_version
from skillspector.llm_utils import is_llm_available

from app.api.routes import scan
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="Skillspector Web API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(scan.router)


@app.get("/health")
def health() -> dict:
    llm_available, _ = is_llm_available()
    return {
        "status": "ok",
        "skillspector_version": skillspector_version,
        "llm_available": llm_available,
    }
