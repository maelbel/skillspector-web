from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from app.core.config import get_settings
from app.core.security import require_admin
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
    schedule,
)

router = APIRouter(prefix="/scan", tags=["scan"])


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
        return value


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
        completed_steps=completed_steps,
        total_steps=TOTAL_GRAPH_STEPS,
    )


@router.post("", response_model=ScanQueuedResponse)
async def start_scan(req: ScanRequest) -> ScanQueuedResponse:
    job = create_job(req.target, req.llm)
    schedule(job)
    return ScanQueuedResponse(id=job.id, status=job.status)


@router.get("", response_model=ScanHistoryResponse)
async def read_scan_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ScanHistoryResponse:
    rows, total = list_jobs(limit, offset)
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
        )
        for row in rows
    ]
    return ScanHistoryResponse(items=items, total=total)


@router.get("/{job_id}", response_model=ScanStatusResponse)
async def read_scan(job_id: str) -> ScanStatusResponse:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return _to_response(job)


@router.get("/{job_id}/logs", response_model=ScanLogsResponse)
async def read_scan_logs(job_id: str) -> ScanLogsResponse:
    return ScanLogsResponse(lines=get_logs(job_id))


@router.delete("/{job_id}", status_code=204, dependencies=[Depends(require_admin)])
async def delete_scan(job_id: str) -> None:
    if not delete_job(job_id):
        raise HTTPException(status_code=404, detail="scan not found")
