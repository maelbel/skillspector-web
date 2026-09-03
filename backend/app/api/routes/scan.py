from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from app.core.config import get_settings
from app.scanner import Job, JobStatus, LLMConfig, create_job, get_job, schedule

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


def _to_response(job: Job) -> ScanStatusResponse:
    return ScanStatusResponse(
        id=job.id,
        target=job.target,
        status=job.status,
        created_at=job.created_at,
        finished_at=job.finished_at,
        result=job.result,
        error=job.error,
    )


@router.post("", response_model=ScanQueuedResponse)
async def start_scan(req: ScanRequest) -> ScanQueuedResponse:
    job = create_job(req.target, req.llm)
    schedule(job)
    return ScanQueuedResponse(id=job.id, status=job.status)


@router.get("/{job_id}", response_model=ScanStatusResponse)
async def read_scan(job_id: str) -> ScanStatusResponse:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="scan not found (it may have expired)")
    return _to_response(job)
