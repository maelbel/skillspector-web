import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, field_validator

from app import claude_key, db, quotas, rate_limit
from app.ai_review import AIReview, ai_review_status
from app.auth import Viewer
from app.auth.deps import CurrentViewer
from app.core.config import get_settings
from app.core.mode import Mode
from app.jobs import JobRejectedError, get_runner
from app.scan_logs import get_logs, get_progress
from app.scanner import (
    TOTAL_GRAPH_STEPS,
    Job,
    JobStatus,
    LLMConfig,
    create_job,
    delete_job,
    get_job,
    list_jobs,
)
from app.targets import raw_file_url

router = APIRouter(prefix="/scan", tags=["scan"])


def _rate_limit_scan(request: Request, viewer: CurrentViewer) -> None:
    """Per signed-in user (per address without accounts), plus a cap per address shared by every
    account signed in from it, so opening more accounts doesn't buy more scans."""
    settings = get_settings()
    window = settings.scan_rate_limit_window_seconds
    subject = rate_limit.subject_key(request, viewer)
    rate_limit.enforce(f"scan:{subject}", settings.scan_rate_limit, window, "You've started a lot of scans")
    if viewer.user_id:
        address = rate_limit.client_key(request)
        rate_limit.enforce(f"scan:ip:{address}", settings.scan_ip_rate_limit, window, "Too many scans from this address")


class ScanRequest(BaseModel):
    target: str
    llm: LLMConfig | None = None

    @field_validator("target")
    @classmethod
    def validate_target(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("target is required")
        if not value.startswith(get_settings().allowed_target_schemes):
            allowed = " or ".join(get_settings().allowed_target_schemes)
            raise ValueError(f"target must start with {allowed} (a Git repo, zip, or file URL)")
        # Stored rewritten too, so the history shows what was actually scanned.
        return raw_file_url(value)


class ScanQueuedResponse(BaseModel):
    id: str
    status: JobStatus


class ScanStatusResponse(BaseModel):
    id: str
    target: str
    status: JobStatus
    created_at: float
    finished_at: float | None
    result: dict | None
    error: str | None
    ai_review: AIReview | None
    completed_steps: int
    total_steps: int


class ScanSummaryResponse(BaseModel):
    id: str
    target: str
    status: JobStatus
    created_at: float
    finished_at: float | None
    error: str | None
    risk_score: float | None
    severity: str | None
    recommendation: str | None
    ai_review: AIReview | None
    completed_steps: int
    total_steps: int


class ScanHistoryResponse(BaseModel):
    items: list[ScanSummaryResponse]
    total: int


class ScanLogsResponse(BaseModel):
    lines: list[str]


def _to_response(job: Job) -> ScanStatusResponse:
    completed_steps = TOTAL_GRAPH_STEPS if job.status == JobStatus.DONE else get_progress(job.id)
    return ScanStatusResponse(
        id=job.id,
        target=job.target,
        status=job.status,
        created_at=job.created_at,
        finished_at=job.finished_at,
        result=job.result,
        error=job.error,
        ai_review=ai_review_status(job.result),
        completed_steps=completed_steps,
        total_steps=TOTAL_GRAPH_STEPS,
    )


def _resolve_llm(llm: LLMConfig | None, viewer: Viewer) -> LLMConfig | None:
    """Apply the mode's provider rules and swap in the user's saved Claude key when asked for."""
    if llm is None:
        return None
    if get_settings().mode is Mode.HOSTED:
        # No shared Claude login, and no server-side requests to arbitrary URLs.
        if llm.provider != "anthropic":
            raise HTTPException(status_code=422, detail="Only Claude (Anthropic) is available for AI review on this server")
        if llm.base_url:
            raise HTTPException(status_code=422, detail="A custom base URL isn't allowed on this server")
    if not llm.use_saved_key:
        return llm
    key = claude_key.saved_key(viewer.user_id) if viewer.user_id and claude_key.available() else None
    if key is None:
        raise HTTPException(status_code=400, detail="Connect your Claude key on your account page first, or paste a key for this scan")
    # Held in memory for this scan only; the queue runner never stores a saved key again.
    return llm.model_copy(update={"api_key": key})


@router.post("", response_model=ScanQueuedResponse, dependencies=[Depends(_rate_limit_scan)])
async def start_scan(req: ScanRequest, viewer: CurrentViewer) -> ScanQueuedResponse:
    limits = quotas.current()
    quotas.ensure_not_paused(limits)
    llm = _resolve_llm(req.llm, viewer)
    runner = get_runner()
    try:
        runner.check(llm)
    except JobRejectedError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if runner.is_full():
        raise HTTPException(status_code=503, detail="The scan queue is full — try again in a few minutes")
    # Last, so a scan refused for any other reason doesn't count towards today's quota.
    quotas.enforce(viewer, limits)
    job = create_job(req.target, llm, owner_id=viewer.user_id)
    try:
        await runner.submit(job)
    except Exception as exc:
        # Don't leave a scan pending forever if it never reached the queue.
        db.update_scan(id=job.id, status=JobStatus.ERROR, finished_at=time.time(), result=None, error="Couldn't queue the scan")
        raise HTTPException(status_code=503, detail="Couldn't queue the scan — try again in a moment") from exc
    return ScanQueuedResponse(id=job.id, status=job.status)


@router.get("", response_model=ScanHistoryResponse)
async def read_scan_history(
    viewer: CurrentViewer,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ScanHistoryResponse:
    # Admins see every scan, including ones from before accounts existed; users only their own.
    rows, total = list_jobs(limit, offset, owner_id=None if viewer.is_admin else viewer.user_id)
    items = [
        ScanSummaryResponse(
            id=row["id"],
            target=row["target"],
            status=row["status"],
            created_at=row["created_at"],
            finished_at=row["finished_at"],
            error=row["error"],
            risk_score=row["risk_score"],
            severity=row["severity"],
            recommendation=row["recommendation"],
            ai_review=row["ai_review"],
            completed_steps=TOTAL_GRAPH_STEPS if row["status"] == JobStatus.DONE else get_progress(row["id"]),
            total_steps=TOTAL_GRAPH_STEPS,
        )
        for row in rows
    ]
    return ScanHistoryResponse(items=items, total=total)


def _visible_scan(job_id: str, viewer: Viewer) -> None:
    """404, not 403, for someone else's scan, so ids can't be probed."""
    scan = db.get_scan(job_id)
    if scan is None or not viewer.can_see(scan):
        raise HTTPException(status_code=404, detail="scan not found")


@router.get("/{job_id}", response_model=ScanStatusResponse)
async def read_scan(job_id: str, viewer: CurrentViewer) -> ScanStatusResponse:
    _visible_scan(job_id, viewer)
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return _to_response(job)


@router.get("/{job_id}/logs", response_model=ScanLogsResponse)
async def read_scan_logs(job_id: str, viewer: CurrentViewer) -> ScanLogsResponse:
    _visible_scan(job_id, viewer)
    return ScanLogsResponse(lines=get_logs(job_id))


@router.delete("/{job_id}", status_code=204)
async def delete_scan(job_id: str, viewer: CurrentViewer) -> None:
    _visible_scan(job_id, viewer)
    if not delete_job(job_id):
        raise HTTPException(status_code=404, detail="scan not found")
